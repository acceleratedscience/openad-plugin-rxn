# OpenAD Plugin - Deep Search

_This is a plugin for [OpenAD](https://github.com/acceleratedscience/open-ad-toolkit)_

<br>

## About RXN

RXN helps you predict chemical reactions, retrosynthesis pathways and experimental procedures. You can train AI models with data for specific chemistry domains.

[rxn.app.accelerate.science](https://rxn.app.accelerate.science) / [GitHub](https://github.com/rxn4chemistry)


<br>

## About this Plugin

This plugin exposes a subset of RXN functionality to the OpenAD client, more specifically:
- Predict reactions between molecules
- Predict retrosynthesis pathways to generate a molecule
- Interpret chemnical recipes and parse them into step-by-step instructions

<br>

## Installation

Regular installation:

    pip install git+https://github.com/acceleratedscience/openad-plugin-rxn

Installation for development:

    git clone git@github.com:acceleratedscience/openad-plugin-rxn.git
    cd openad-plugin-rxn
    pip install -e .