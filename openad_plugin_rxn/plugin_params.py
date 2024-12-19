# Displayed above the list of library commands in the help.
# - - -
# Keep this as short as possible, as it is also used to
# list the commands of your library, eg. `plugin demo ?`
PLUGIN_NAME = "RXN"

# Snake case name of the library, only used internally.
# - - -
# Avoid to use the word "plugin" to prevent redundancy.
PLUGIN_KEY = "rxn"

# Namespace for your plugin commands
# - - -
# A short word that will be required in front of every command.
# Can be left blank but this is not recommended.
PLUGIN_NAMESPACE = "rx"

# Optional: A note that will display at the bottom of your command's help description.
# - - -
# This can either be a string, or a dictionary with localized strings.
CMD_NOTE = "<reset><reverse> i </reverse></reset> To see all available RXN commands, run <cmd>rxn ?</cmd>"


# Clauses that are repeated across the descriptions of multiple commands.
CLAUSES = {
    "save_as": "Use the <cmd>save as</cmd> clause to save the results as a csv file in your current workspace.",
}
