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
- Interpret chemical recipes and parse them into step-by-step instructions

<br>

## Installation

Regular installation:

    pip install git+https://github.com/acceleratedscience/openad-plugin-rxn

Installation for development:

    git clone git@github.com:acceleratedscience/openad-plugin-rxn.git
    cd openad-plugin-rxn
    pip install -e .

## Login

In order to use this plugin, you need to register for an RXN account.

1. First, you'll need to generate an API key on the RXN website.

    - Sign up for an RXN account at [rxn.app.accelerate.science](https://rxn.app.accelerate.science)
    - Obtain your API key by clicking the user profile icon in the top right hand corner and select "Account", then select the "My keys" tab.<br>
      <br>
      <a href="assets/rxn-api-key.png" target="_blank"><img src="assets/rxn-api-key.png" /></a>

2. When using any of the RXN commands, you'll be promted for your credentials.

    - **Hostname:** Default: [https://rxn.app.accelerate.science](https://rxn.app.accelerate.science)<br>
    - **API_key:** The RXN API key you obtained following the instructions above.

3. You should get a message saying you successfully logged in.<br>

    > **Note:** To reset your credentials, run `rxn reset login`