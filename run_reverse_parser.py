from reverse_parser import Reverse_Parser
from uuid import UUID

tree = ('start', [('statements', [('statement', [('simple_stmt', [('targets', ('NAME', 0)), ('simple_stmt_0', [('terminal_8', ('=', 1)), ('assignment_plus_continuation_1', ('NUMBER', 2))])]), ('simple_stmts_join_continuation_1', ('NEWLINE', 3))]), ('statements_plus_continuation_1', [('terminal_67', ('if', 4)), ('statements_plus_continuation_1_28', [('expression', ('NAME', UUID('f319422d-0db7-43eb-8e59-2aea6e1f2c51'))), ('statements_plus_continuation_1_29', [('terminal_16', (':', 5)), ('block', [('terminal_11', ('NEWLINE', 6)), ('block_0', [('terminal_6', ('INDENT', 7)), ('block_1', [('statements', [('simple_stmt', [('term', ('NUMBER', 8)), ('sum_rest', [('terminal_24', ('+', 9)), ('term', ('NUMBER', 10))])]), ('simple_stmts_join_continuation_1', ('NEWLINE', 11))]), ('terminal_5', ('DEDENT', 12))])])])])])])]), ('terminal_53', ('ENDMARKER', 13))])
mapping = {0: 'x', 1: '=', 2: '1', 3: 'NEWLINE', 4: 'if', 5: ':', 6: 'NEWLINE', 7: 'INDENT', 8: '2', 9: '+', 10: '3', 11: 'NEWLINE', 12: 'DEDENT', 13: 'ENDMARKER'}
values = {'NAME': ['x'], 'NUMBER': ['1', '2', '3']}

rev_parser = Reverse_Parser(tab_spaces=2)

rev = rev_parser.reverse_parse(tree, mapping, values)

print('PARSE TREE CODE')
print(f'{rev}')