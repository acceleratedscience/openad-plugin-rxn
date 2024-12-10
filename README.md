# OpenAD Plugin - Deep Search

_This is a plugin for [OpenAD](https://github.com/acceleratedscience/open-ad-toolkit)_

<br>

## About Deep Search

Deep Search (aka DS4SD) is developed at IBM Research and leverages state-of-the-art AI methods to continuously collect, convert, enrich, and link large document collections. You can use it for both public and proprietary PDF documents.

[ds4sd.github.io](https://ds4sd.github.io/) / [GitHub](https://github.com/DS4SD) / [IBM Research](https://research.ibm.com/projects/deep-search)

<br>

## About this Plugin

This plugin exposes a subset of Deep Search functionality to the OpenAD client, more specifically:
- Finding molecules by similarity or substructure
- Scanning patents for molecules, or find patents containing a certain molecule
- List and search available Deep Search collections like arXiv abstracts, PubChem or USPTO patents and more

<br>

## Installation

Regular installation:

    pip install git+https://github.com/acceleratedscience/openad-plugin-ds

Installation for development:

    git clone git@github.com:acceleratedscience/openad-plugin-ds.git
    cd openad-plugin-ds
    pip install -e .