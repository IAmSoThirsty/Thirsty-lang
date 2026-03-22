[
  "drink"
  "pour"
  "sip"
  "return"
] @keyword

[
  "thirsty"
  "hydrated"
  "refill"
  "cascade"
] @keyword.control

[
  "glass"
  "fountain"
] @keyword.function

[
  "ENCODE"
  "DECODE"
  "PARITY"
  "VALIDATE"
  "BIJECTIVITY"
  "ING"
  "COG"
  "D_NT"
  "SHD"
  "INV"
  "CAP"
  "QRM_LINEAR"
  "COM"
  "ANC"
  "LED"
  "T_BLOB"
] @keyword.directive

(comment) @comment
(string) @string
(number) @number
(boolean) @constant.builtin

(variable_declaration
  name: (identifier) @variable)

(assignment_statement
  target: (identifier) @variable)

(function_definition
  name: (identifier) @function)

(async_function_definition
  name: (identifier) @function)

(class_definition
  name: (identifier) @type)

(call_expression
  function: (identifier) @function.call)

(member_expression
  property: (identifier) @property)
