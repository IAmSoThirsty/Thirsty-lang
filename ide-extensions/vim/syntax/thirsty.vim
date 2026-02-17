" Vim syntax file for Thirsty-Lang
" Language: Thirsty-Lang (TARL)
" Maintainer: Thirsty-Lang Team
" Latest Revision: 2026

if exists("b:current_syntax")
  finish
endif

" Keywords
syn keyword thirstyKeyword if else elif for while break continue return
syn keyword thirstyKeyword class def import from as try except finally
syn keyword thirstyKeyword with lambda yield async await
syn keyword thirstyConstant True False None
syn keyword thirstyType int str float bool list dict set tuple

" Comments
syn match thirstyComment "#.*$"

" Strings
syn region thirstyString start='"' end='"' skip='\\"'
syn region thirstyString start="'" end="'" skip="\\'"

" Numbers
syn match thirstyNumber "\v<\d+>"
syn match thirstyNumber "\v<\d+\.\d+>"

" Operators
syn match thirstyOperator "\v[+\-*/%=<>!&|~^]"
syn keyword thirstyOperator and or not in is

" Functions
syn match thirstyFunction "\v<\w+>\s*\ze\("

" Highlighting
hi def link thirstyKeyword Keyword
hi def link thirstyConstant Constant
hi def link thirstyType Type
hi def link thirstyComment Comment
hi def link thirstyString String
hi def link thirstyNumber Number
hi def link thirstyOperator Operator
hi def link thirstyFunction Function

let b:current_syntax = "thirsty"
