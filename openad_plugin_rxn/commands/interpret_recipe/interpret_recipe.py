import os

# OpenAD
from openad.app.global_var_lib import GLOBAL_SETTINGS
from openad.helpers.spinner import spinner
from openad.helpers.output import output_text, output_error

# Plugin
from openad_plugin_rxn.plugin_params import PLUGIN_KEY
from openad_plugin_rxn.plugin_master_class import RXNPlugin


class InterpretRecipe(RXNPlugin):

    def __init__(self, cmd_pointer, cmd: dict):
        """
        Parameters
        ----------
        cmd_pointer:
            The command pointer object
        cmd: dict
            Parser inputs from pyparsing as a dictionary
        """
        super().__init__(cmd_pointer)
        self.cmd = cmd

    def run(self):
        """
        Interpret a free text paragraph into a recipe list of instructions.
        """

        # Define the RXN API
        api = self.cmd_pointer.login_settings["client"][self.cmd_pointer.login_settings["toolkits"].index(PLUGIN_KEY)]

        recipe = self.cmd["recipe"]
        recipe_file_path = self.cmd_pointer.workspace_path() + "/" + recipe.strip()
        is_file = os.path.isfile(recipe_file_path)

        # Recipe from file
        if is_file:
            spinner.start(f"Processing <yellow>{recipe}</yellow>")

            # Read recipe from file
            with open(recipe_file_path, "r", encoding="utf-8") as handle:
                recipe = handle.read()

        # Recipe from string
        else:
            spinner.start("Processing paragraph")

        # Compile recipe steps
        try:
            # raise Exception('This is a test error')
            recipe_steps = []
            actios_from_procedure_results = api.paragraph_to_actions(recipe)
            if not actios_from_procedure_results["actions"]:
                raise ValueError("No actions found in the provided paragraph")
            recipe_steps.append("<h1>Recipe steps:</h1>")
            for index, action in enumerate(actios_from_procedure_results["actions"], 1):
                recipe_steps.append(f"{index}. {action}")
            recipe_steps_str = "\n".join(recipe_steps)
            spinner.stop()
        except Exception as err:  # pylint: disable=broad-exception-caught
            spinner.stop()
            output_error(["Failed to parse the provided paragraph", err], return_val=False)
            return

        # Return data for API
        if GLOBAL_SETTINGS["display"] == "api":
            return recipe_steps

        # Display results in CLI & Notebook
        else:
            output_text(recipe_steps_str, pad=1, nowrap=True, return_val=False)
