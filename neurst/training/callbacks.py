# Copyright 2020 ByteDance Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import csv
import time
import traceback
from abc import ABCMeta

import numpy
import six
import tensorflow as tf
from absl import logging
from tensorflow.python.keras import backend as K
from tensorflow.python.ops import summary_ops_v2

from neurst.layers.metric_layers import METRIC_REDUCTION, get_metric_reduction
from neurst.utils import compat
from neurst.utils.configurable import ModelConfigs


@six.add_metaclass(ABCMeta)
class CentralizedCallback(tf.keras.callbacks.Callback):
    """ Custom base Callback for handling global step. """

    def __init__(self, step_counter=None, csv_output_dir=None):
        super(CentralizedCallback, self).__init__()
        self.csv_file = csv_output_dir
        if step_counter is not None:
            self.__global_step = step_counter
        else:
            self.__global_step = compat.get_max_training_step(self.csv_file)

    def on_train_begin(self, logs=None):
        super(CentralizedCallback, self).on_train_begin(logs)
        if self.__global_step is None or isinstance(self.__global_step, int) and self.__global_step < 1:
            self.__global_step = compat.get_max_training_step(self.csv_file)

    def on_train_batch_begin(self, batch, logs=None):
        if self.__global_step is not None:
            if isinstance(self.__global_step, int):
                self.__global_step += 1
            else:
                self.__global_step.assign_add(1)
        self.custom_on_train_batch_begin(self.__global_step, logs)

    def on_train_batch_end(self, batch, logs=None):
        self.custom_on_train_batch_end(self.__global_step, logs)

    def custom_on_train_batch_begin(self, step, logs=None):
        pass

    def custom_on_train_batch_end(self, step, logs=None):
        pass


class CustomCheckpointCallback(CentralizedCallback):
    """ Defines custom checkpoint callback for automatically saving checkpoints.
        It DOES NOT support multi-worker mirrored strategy.
    """

    def __init__(self,
                 model_configs,
                 save_checkpoint_steps=1000,
                 checkpoint_manager=None,
                 step_counter=None,
                 csv_output_dir=None):
        """ Initializes custom checkpoint callback.

        Args:
            model_configs: A dict of configurations for restoring.
            save_checkpoint_steps: An int scalar, saving checkpoint this every steps.
            checkpoint_manager: A CheckpointManager instance.
        """
        super(CustomCheckpointCallback, self).__init__(step_counter=step_counter, csv_output_dir=csv_output_dir)
        self._checkpoint_manager = checkpoint_manager
        if self._checkpoint_manager is None:
            self._checkpoint_manager = compat.get_saver_or_default()
        self._model_configs = model_configs
        self._save_checkpoint_steps = save_checkpoint_steps

    def on_train_begin(self, logs=None):
        super(CustomCheckpointCallback, self).on_train_begin(logs)
        ModelConfigs.dump(self._model_configs, output_dir=self._checkpoint_manager.directory)

    def custom_on_train_batch_end(self, step, logs=None):
        """ Save checkpoints. """
        _ = logs
        if step % self._save_checkpoint_steps == 0:
            start_time = time.time()
            try:
                path = self._checkpoint_manager.save(step)
            except tf.errors.OpError:
                logging.info(traceback.format_exc())
                logging.info("Fail to save checkpoint.")
            else:
                logging.info("Saved checkpoint into %s\tElapsed %.2fs", path, time.time() - start_time)


class LearningRateScheduler(CentralizedCallback):
    """ Custom learning rate scheduler which adapts by steps. """

    def __init__(self, lr_schedule):
        """ Initializes. """
        super(LearningRateScheduler, self).__init__()
        logging.info("Wrapper lr schedule with the callback LearningRateScheduler.")
        self._lr_schedule = lr_schedule

    def custom_on_train_batch_end(self, step, logs=None):
        if not hasattr(self.model.optimizer, 'lr'):
            raise ValueError('Optimizer must have a "lr" attribute.')
        lr = self._lr_schedule(step)
        if not (compat.is_tf_tensor(lr) or isinstance(lr, (float, numpy.float32, numpy.float64))):
            raise ValueError('The output of the "schedule" function '
                             'should be float.')
        if compat.is_tf_tensor(lr) and not lr.dtype.is_floating:
            raise ValueError('The dtype of Tensor should be float')
        K.set_value(self.model.optimizer.lr, K.get_value(lr))


class MetricReductionCallback(CentralizedCallback):

    def __init__(self, strategy, summary_steps, log_dir,
                 device='', lr_schedule=None, save_checkpoint_steps=1000):
        super(MetricReductionCallback, self).__init__()
        self._summary_steps = summary_steps
        self._save_checkpoint_steps = save_checkpoint_steps  # Added to determine when to save CSV
        self._log_dir = log_dir
        self._file_writer = tf.summary.create_file_writer(self._log_dir)
        self._file_writer.set_as_default()
        self._lr_schedule = lr_schedule
        self._should_summary = (compat.get_distributed_worker_setting()[0] == 0)
        # logging
        self._last_triggered_time = None
        self._accumulated_time_secs = 0.
        self._last_triggered_metric = None
        # for allreduce
        self._strategy = strategy
        self._device = device
        self._m_vars = {}
        self._allreduce_ops = {}
        self._allreduce_ranks = 1.
        self.training_data = []
        self.csv_file = 'output/training_data.csv'

    def on_train_begin(self, logs=None):
        """ At the begining of training, write the graph to the tensorboard. """
        super(MetricReductionCallback, self).on_train_begin(logs)
        if self._should_summary:
            summary_ops_v2.graph(K.get_graph())

    def custom_on_train_batch_begin(self, step, logs=None):
        self._last_triggered_time = time.time()

    def _byteps_average_metrics_in_place(self, logs):
        logs = logs or {}
        reduced_logs = {}
        import byteps.tensorflow as bps

        if self._allreduce_ranks <= 1.:
            self._allreduce_ranks = float(bps.size())
        # Reduce every metric among workers. Sort metrics by name
        # to ensure consistent order.
        for metric, value in sorted(logs.items()):
            from tensorflow.python.eager import context
            if context.executing_eagerly():
                with tf.device(self._device):
                    reduced_logs[metric] = bps.push_pull(K.constant(value, name=metric),
                                                         op=bps.ops.ReduceOps.Sum).numpy()
            else:
                if metric not in self.variables:
                    with tf.name_scope('MetricAverageCallback') as scope:
                        var = tf.Variable(value, name=metric)
                        K.get_session().run(var.initializer)
                        self._m_vars[metric] = var
                        self._allreduce_ops[metric] = bps.push_pull(var, scope, device_dense=self._device,
                                                                    op=bps.ops.ReduceOps.Sum)
                else:
                    K.set_value(self._m_vars[metric], value)
                reduced_logs[metric] = K.get_session().run(self._allreduce_ops[metric])

        # Override the reduced values back into logs dictionary
        # for other callbacks to use.
        for metric, value in reduced_logs.items():
            logs[metric] = value / self._allreduce_ranks

    def _horovod_average_metrics_in_place(self, logs):
        logs = logs or {}
        reduced_logs = {}
        import horovod.tensorflow as hvd

        if self._allreduce_ranks <= 1.:
            self._allreduce_ranks = float(hvd.size())
        # Reduce every metric among workers. Sort metrics by name
        # to ensure consistent order.
        for metric, value in sorted(logs.items()):
            from tensorflow.python.eager import context
            if context.executing_eagerly():
                reduced_logs[metric] = hvd.allreduce(K.constant(value, name=metric)).numpy()
            else:
                if metric not in self._m_vars:
                    with K.name_scope('MetricAverageCallback'):
                        var = K.variable(value, name=metric)
                        K.get_session().run(var.initializer)
                        self._m_vars[metric] = var
                        self._allreduce_ops[metric] = hvd.allreduce(var, device_dense=self._device)
                else:
                    K.set_value(self._m_vars[metric], value)
                reduced_logs[metric] = K.get_session().run(self._allreduce_ops[metric])
        # Override the reduced values back into logs dictionary
        # for other callbacks to use.
        for metric, value in reduced_logs.items():
            logs[metric] = value

    def _write_metrics_to_csv(self):
        """Write the training metrics to a CSV file while saving the checkpoint."""
        try:
            with open(self.csv_file, 'w', newline='') as csvfile:
                fieldnames = ['step', 'loss', 'lr', 'accuracy']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in self.training_data:
                    writer.writerow(row)
            logging.info(f"Training metrics successfully written to {self.csv_file}.")
        except IOError as e:
            logging.error(f"Failed to write training metrics to {self.csv_file}. IOError: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred while writing training metrics to {self.csv_file}: {e}")

    def custom_on_train_batch_end(self, step, logs=None):
        if isinstance(step, tf.Tensor):
            # It's a TensorFlow tensor; now check if it's specifically an int64 type
            if step.dtype == tf.int64:
                # Convert it to a numpy array and get the Python native type, e.g., int
                step = step.numpy().item()
        super(MetricReductionCallback, self).custom_on_train_batch_end(step, logs)
        # Record and log the time taken to handle TensorFlow Tensor conversion
        tf_tensor_conversion_time = time.time() - self._last_triggered_time
        logging.info(f"TensorFlow Tensor conversion took {tf_tensor_conversion_time:.4f} seconds at step {step}")
        self._accumulated_time_secs += time.time() - self._last_triggered_time
        if step % self._summary_steps == 0:
            if self._strategy == "horovod":
                self._horovod_average_metrics_in_place(logs)
            elif self._strategy == "byteps":
                self._byteps_average_metrics_in_place(logs)
            if self._should_summary:
                current_data = {
                    "step": step,
                    "loss": logs["loss"],
                    "lr": self._lr_schedule(step - 1).numpy() if self._lr_schedule is not None else None,
                    "accuracy": logs["accuracy"] if "accuracy" in logs else None
                }
                self.training_data.append(current_data)

                logging_metrics = {"step": step}
                if self._lr_schedule is not None:
                    logging_metrics["lr"] = self._lr_schedule(step - 1).numpy()
                for metric, value in logs.items():
                    reduction = get_metric_reduction(metric)
                    if reduction == METRIC_REDUCTION.MEAN:
                        logging_metrics[metric] = value
                    else:
                        assert reduction == METRIC_REDUCTION.SUM, (
                            f"Unknown reduction type of {metric}: {type(metric)}")
                        if self._last_triggered_metric is None:
                            self._last_triggered_metric = {}
                        this_metric_value = value - self._last_triggered_metric.get(metric, 0.)
                        this_metric_value *= self._allreduce_ranks
                        self._last_triggered_metric[metric] = value
                        logging_metrics[metric + "_per_step"] = this_metric_value / float(self._summary_steps)
                        logging_metrics[metric + "_per_sec"] = this_metric_value / self._accumulated_time_secs
                logging.info(logging_metrics)
                logging_metrics.pop("step")
                try:
                    for metric, value in logging_metrics.items():
                        tf.summary.scalar(compat.GlobalKeys.TBPREFIX_TRAINING + f"/{metric}", value, step=step)
                except tf.errors.OpError:
                    logging.info("Fail to summary metrics.")
            self._accumulated_time_secs = 0.
        if step % self._save_checkpoint_steps == 0:
            # Writing to CSV every save_checkpoint_steps steps
            self._write_metrics_to_csv()
