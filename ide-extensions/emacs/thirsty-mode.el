;;; thirsty-mode.el --- Major mode for Thirsty-Lang  -*- lexical-binding: t; -*-

;; Copyright (C) 2026 Thirsty-Lang Team
;; Author: Thirsty-Lang Team
;; Keywords: languages
;; Version: 1.0.0

;;; Commentary:
;; Major mode for editing Thirsty-Lang (TARL) files

;;; Code:

(defvar thirsty-mode-syntax-table
  (let ((table (make-syntax-table)))
    ;; Comments
    (modify-syntax-entry ?# "<" table)
    (modify-syntax-entry ?\n ">" table)
    ;; Strings
    (modify-syntax-entry ?\" "\"" table)
    (modify-syntax-entry ?\' "\"" table)
    table)
  "Syntax table for `thirsty-mode'.")

(defconst thirsty-keywords
  '("if" "else" "elif" "for" "while" "break" "continue" "return"
    "class" "def" "import" "from" "as" "try" "except" "finally"
    "with" "lambda" "yield" "async" "await"))

(defconst thirsty-constants
  '("True" "False" "None"))

(defconst thirsty-types
  '("int" "str" "float" "bool" "list" "dict" "set" "tuple"))

(defvar thirsty-font-lock-keywords
  `((,(regexp-opt thirsty-keywords 'words) . font-lock-keyword-face)
    (,(regexp-opt thirsty-constants 'words) . font-lock-constant-face)
    (,(regexp-opt thirsty-types 'words) . font-lock-type-face)
    ("\\<[0-9]+\\(\\.[0-9]+\\)?\\>" . font-lock-constant-face)
    ("\\<\\(def\\|class\\)\\s-+\\(\\sw+\\)" 2 font-lock-function-name-face)))

;;;###autoload
(define-derived-mode thirsty-mode prog-mode "Thirsty"
  "Major mode for editing Thirsty-Lang files."
  :syntax-table thirsty-mode-syntax-table
  (setq-local comment-start "#")
  (setq-local comment-start-skip "#+\\s-*")
  (setq-local font-lock-defaults '(thirsty-font-lock-keywords))
  (setq-local indent-tabs-mode nil)
  (setq-local tab-width 4))

;;;###autoload
(add-to-list 'auto-mode-alist '("\\.tarl\\'" . thirsty-mode))
(add-to-list 'auto-mode-alist '("\\.tl\\'" . thirsty-mode))

(provide 'thirsty-mode)
;;; thirsty-mode.el ends here
