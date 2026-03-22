(function_definition
  parameters: (parameter_list
    (identifier) @local.definition.parameter))

(async_function_definition
  parameters: (parameter_list
    (identifier) @local.definition.parameter))

(variable_declaration
  name: (identifier) @local.definition.var)

(assignment_statement
  target: (identifier) @local.reference)

(identifier) @local.reference
