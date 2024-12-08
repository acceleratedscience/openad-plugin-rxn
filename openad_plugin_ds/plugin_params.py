# Displayed above the list of library commands in the help.
# - - -
# Keep this as short as possible, as it is also used to
# list the commands of your library, eg. `plugin demo ?`
PLUGIN_NAME = "Deep Search"

# Snake case name of the library, only used internally.
# - - -
# Avoid to use the word "plugin" to prevent redundancy.
PLUGIN_KEY = "deep_search"

# Namespace for your plugin commands
# - - -
# A short word that will be required in front of every command.
# Can be left blank but this is not recommended.
PLUGIN_NAMESPACE = "ds"

# Optional: A note that will display at the bottom of your command's help description.
# - - -
# This can either be a string, or a dictionary with localized strings.
CMD_NOTE = (
    "<reset><reverse> i </reverse></reset> To see all available Deep Search commands, run <cmd>deep search ?</cmd>"
)


# Clauses that are repeated across the descriptions of multiple commands.
CLAUSES = {
    # "using": "Note: The <cmd>USING</cmd> clause requires all enclosed parameters to be defined in the same order as listed below.",
    # "using": "Note: All enclosed parameters should be defined in the same order as listed below.",
    "save_as": "Use the <cmd>save as</cmd> clause to save the results as a csv file in your current workspace.",
    "list_collections": "Run <cmd>list all collections</cmd> to list available collections.",
    "list_domains": "Use the command <cmd>list all collections</cmd> to find available domains.",
}
