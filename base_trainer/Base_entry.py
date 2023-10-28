from abc import ABCMeta, abstractmethod

import six


@six.add_metaclass(ABCMeta)
class BaseEntry(object):
    REGISTRY_NAME = "entry"

    def __init__(self, strategy, model, task, custom_dataset, model_dir):
        """ Initializes the basic experiment for training, evaluation, etc. """
        self._strategy = strategy
        self._model = model
        self._model_dir = model_dir
        self._task = task
        self._custom_dataset = custom_dataset

    @property
    def strategy(self):
        return self._strategy

    @property
    def model(self):
        return self._model

    @property
    def task(self):
        return self._task

    @property
    def custom_dataset(self):
        return self._custom_dataset

    @property
    def model_dir(self):
        return self._model_dir

    @abstractmethod
    def run(self):
        """ Running the method. """
        raise NotImplementedError
