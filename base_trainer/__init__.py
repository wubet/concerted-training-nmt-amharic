import importlib
import os

from base_trainer.Base_entry import BaseEntry
from neurst.utils.registry import setup_registry

build_base_trainer, register_base_trainer = setup_registry(BaseEntry.REGISTRY_NAME, base_class=BaseEntry,
                                                           verbose_creation=True)

models_dir = os.path.dirname(__file__)
for file in os.listdir(models_dir):
    path = os.path.join(models_dir, file)
    if not file.startswith('_') and not file.startswith('.') and file.endswith('.py'):
        model_name = file[:file.find('.py')] if file.endswith('.py') else file
        module = importlib.import_module('base_trainer.' + model_name)
