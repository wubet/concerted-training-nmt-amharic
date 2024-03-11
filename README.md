# Amharic-English Concerted training NMT

The Amharic-English Concerted training NMT (Neural Machine Translation) architecture is developed based on the "Concerted Training Neural Machine Translation (CTNMT)" architecture, which incorporates novel techniques such as "dynamic switch" and "rate schedule" in its training methodology. Moreover, it enhances NMT translation effectiveness by incorporating insights from BERT (Bidirectional Encoder Representations from Transformers), a groundbreaking pre-training model.

Here's a simplified breakdown of the components involved:

1.	Neural Machine Translation (NMT): This method employs extensive neural networks for machine translation, significantly enhancing translation quality by processing entire texts as cohesive units. This advancement results in translations that are both more fluent and accurate.

2.	BERT Pre-training Model: BERT revolutionizes the way language representations are pre-trained, excelling in a variety of natural language processing (NLP) tasks. It models the context surrounding each word by considering the surrounding words, diverging from older models that could only process text in a single direction. Utilizing BERT within NMT frameworks can greatly improve the grasp of linguistic subtleties, thereby enhancing translation accuracy.

The architecture integrates BERT's pre-trained language understanding with NMT aims to provide a more nuanced understanding of both source and target languages. This approach is beneficial for languages with less digital resources, like Amharic, by boosting the model's ability to understand and translate contextually rich and complex sentences.

The architecture's design emphasizes the harmonization of various training elements to refine the translation workflow. It includes:


•	Dynamic Switch: This refers to a method where the training process dynamically switches between different modes or focuses. For instance, it might alternate between focusing on learning from context (like BERT's approach) and direct translation tasks. This adaptability could help the model learn more efficiently.

•	Rate Schedule: This refers to a planned variation in learning rates over the course of training. By adjusting these rates according to a predetermined schedule, the model potentially avoids local minima and improves its learning outcomes.

### Architecture Overview

The "Amharic-English Concerted Training NMT" utilizes the neurst toolkit to construct its foundation, drawing upon the [CTNMT model architecture](https://github.com/bytedance/neurst/tree/master/examples/ctnmt) repository as detailed in [Towards Making the Most of BERT in Neural Machine Translation](https://arxiv.org/abs/1908.05672)" 

### Requirements and Installation:
Tensorflow version = 2.4.0 \
Python 3.8 <= version >= 3.4

Cloning and Building the Repository:

Repo cloning:
```commandline
https://github.com/wubet/concerted-training-nmt-amharic.git
```
Installs all the dependencies
```commandline
pip3 install -r requirements.txt
```


### Data Preparation

Clone the English-Amharic corpus.
```commandline
Git clone https://github.com/wubet/unified-amharic-english-corpus.git
```
This step includes cleaning the data (removing unnecessary characters, normalizing text, etc.), tokenizing sentences (breaking text down into smaller parts like words or subwords), and applying more advanced text processing techniques to improve model training efficiency. 

Preprocessing training data:
```commandline
python3 data/bilingual_data_processor.py \
--original_path=../unified-amharic-english-corpus/datasets/train.am-en.base.en
--destination_dir=../tmp/data
--source_language_alias=en
--target_language_alias=am
--task=train
```

Preprocessing test data:
```commandline
python3 data/bilingual_data_processor.py \
--original_path=../unified-amharic-english-corpus/datasets/train.am-en.base.en
--destination_dir=../tmp/data
--source_language_alias=en
--target_language_alias=am
--task=test
```

Preparing Amharic translitration file for training
```commandline
python3 translitration/create_transliteration.py
--source_filenames=unified-amharic-english-corpus/datasets/train.am-en.base.en \
--target_filenames=unified-amharic-english-corpus/datasets/train.am-en.transliteration.am
```
Preparing Amharic translitration file for testing
```commandline
python3 ../translitration/create_transliteration.py
--source_filenames=unified-amharic-english-corpus/datasets/test.am-en.base.en \
--target_filenames=unified-amharic-english-corpus/datasets/test.am-en.transliteration.am
```
### Train the Model
Train the model:
```commandline
python3 run_trainer:
--config_paths=configs/dynamic_switch.yaml
--model_dir=tmp/dynamic_switch/best
```