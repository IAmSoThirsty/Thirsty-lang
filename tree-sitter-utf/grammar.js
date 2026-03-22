const PREC = {
  assignment: 1,
  logical_or: 2,
  logical_and: 3,
  equality: 4,
  comparison: 5,
  additive: 6,
  multiplicative: 7,
  call: 8,
};

module.exports = grammar({
  name: "utf",

  extras: ($) => [/\s/, $.comment],

  word: ($) => $.identifier,

  rules: {
    source_file: ($) => repeat($._statement),

    _statement: ($) =>
      choice(
        $.variable_declaration,
        $.assignment_statement,
        $.output_statement,
        $.input_statement,
        $.return_statement,
        $.if_statement,
        $.loop_statement,
        $.function_definition,
        $.async_function_definition,
        $.class_definition,
        $.directive_statement,
        $.expression_statement,
        $.block
      ),

    block: ($) => seq("{", repeat($._statement), "}"),

    variable_declaration: ($) =>
      seq("drink", field("name", $.identifier), optional(seq("=", field("value", $.expression)))),

    assignment_statement: ($) =>
      prec.right(
        PREC.assignment,
        seq(field("target", choice($.identifier, $.member_expression)), "=", field("value", $.expression))
      ),

    output_statement: ($) => seq("pour", field("value", $.expression)),

    input_statement: ($) => seq("sip", optional(field("value", $.expression))),

    return_statement: ($) => seq("return", optional(field("value", $.expression))),

    if_statement: ($) =>
      seq(
        "thirsty",
        field("condition", $.expression),
        field("consequence", $.block),
        optional(seq("hydrated", field("alternative", choice($.block, $.if_statement))))
      ),

    loop_statement: ($) =>
      seq("refill", field("condition", $.expression), field("body", $.block)),

    function_definition: ($) =>
      seq(
        "glass",
        field("name", $.identifier),
        field("parameters", $.parameter_list),
        field("body", $.block)
      ),

    async_function_definition: ($) =>
      seq(
        "cascade",
        "glass",
        field("name", $.identifier),
        field("parameters", $.parameter_list),
        field("body", $.block)
      ),

    class_definition: ($) =>
      seq("fountain", field("name", $.identifier), field("body", $.block)),

    parameter_list: ($) =>
      seq("(", optional(seq($.identifier, repeat(seq(",", $.identifier)))), ")"),

    argument_list: ($) =>
      seq("(", optional(seq($.expression, repeat(seq(",", $.expression)))), ")"),

    directive_statement: ($) =>
      seq(
        choice(
          "ENCODE",
          "DECODE",
          "PARITY",
          "VALIDATE",
          "BIJECTIVITY",
          "ING",
          "COG",
          "D_NT",
          "SHD",
          "INV",
          "CAP",
          "QRM_LINEAR",
          "COM",
          "ANC",
          "LED",
          "T_BLOB"
        ),
        repeat1($.expression)
      ),

    expression_statement: ($) => $.expression,

    expression: ($) =>
      choice(
        $.binary_expression,
        $.call_expression,
        $.member_expression,
        $.identifier,
        $.string,
        $.number,
        $.boolean,
        $.array
      ),

    call_expression: ($) =>
      prec(
        PREC.call,
        seq(field("function", choice($.identifier, $.member_expression)), field("arguments", $.argument_list))
      ),

    member_expression: ($) =>
      prec.left(PREC.call, seq(field("object", $.identifier), ".", field("property", $.identifier))),

    binary_expression: ($) =>
      choice(
        prec.left(PREC.logical_or, seq($.expression, "||", $.expression)),
        prec.left(PREC.logical_and, seq($.expression, "&&", $.expression)),
        prec.left(PREC.equality, seq($.expression, choice("==", "!=", ":="), $.expression)),
        prec.left(PREC.comparison, seq($.expression, choice(">", "<", ">=", "<="), $.expression)),
        prec.left(PREC.additive, seq($.expression, choice("+", "-"), $.expression)),
        prec.left(PREC.multiplicative, seq($.expression, choice("*", "/"), $.expression)),
        prec.left(PREC.call, seq($.expression, "->", $.expression))
      ),

    array: ($) => seq("[", optional(seq($.expression, repeat(seq(",", $.expression)))), "]"),

    boolean: () => choice("true", "false"),

    identifier: () => /[A-Za-z_][A-Za-z0-9_]*/,

    number: () => /\d+(\.\d+)?/,

    string: () =>
      token(
        choice(
          seq('"', repeat(choice(/[^"\\]+/, /\\./)), '"'),
          seq("'", repeat(choice(/[^'\\]+/, /\\./)), "'")
        )
      ),

    comment: () =>
      token(
        choice(
          seq("//", /.*/),
          seq("/*", /[^*]*\*+([^/*][^*]*\*+)*/, "/")
        )
      ),
  },
});
