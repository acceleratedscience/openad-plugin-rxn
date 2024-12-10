# OpenAD Plugin - Deep Search

__This is a plugin for [OpenAD](https://github.com/acceleratedscience/open-ad-toolkit).__

<br>

## About Deep Search

Deep Search leverages state-of-the-art AI methods to continuously collect, convert, enrich, and link large document collections. You can use it for both public and proprietary PDF documents.

[Website](https://ds4sd.github.io/)<br>
[GitHub](https://github.com/DS4SD)

<br>

## About this Plugin

This plugin exposes a subset of Deep Search functionality to the OpenAD client, more specifically:
- Finding molecules by similarity or substructure
- Scanning patents for molecules, or find patents containing a certain molecule
- List and search available Deep Search collections like arXiv abstracts, PubChem or USPTO patents and more.

<br>

## Installation

Regular installation:

    pip install git+https://github.com/acceleratedscience/openad-plugin-ds

Installation for development:

    git clone git@github.com:acceleratedscience/openad-plugin-ds.git
    cd openad-plugin-ds
    pip install -e .