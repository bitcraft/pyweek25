import shlex
from inspect import signature

from . import simplefsm

op_wait = '!w!'
op_option = '!o!'
op_store = '!s!'
op_set = '!t!'

option_token = '/'
set_token = '='
dict_token = ':'


class CommandParser:
    def __init__(self, operations, initial=None):
        self._op_map = dict()
        events = [('reset', '*', op_wait)]
        for parent, cmd in operations:
            print(parent, cmd)
            events.extend(self._program_command(parent, cmd))
        self._psm = simplefsm.SimpleFSM(events, initial)

    def __call__(self, args):
        psm = self._psm
        psm('reset')
        stack = list()
        tokenizer = shlex.shlex(args)
        tokenizer.wordchars += ":."

        for token in tokenizer:
            try:
                psm(token)

            except ValueError:
                op = psm.state[:3]

                if op == op_option:
                    # bad argument
                    raise ValueError(token)

                elif stack:
                    # unexpected argument
                    raise ValueError(token)

                else:
                    # syntax error
                    raise SyntaxError(token)

            op = psm.state[:3]
            print(psm.state, token)
            if op == op_wait:
                stack.append([token, {}])

            elif op == op_store:
                stack[-1][1][token] = True

        print(stack)
        self._run(stack)

    def _run(self, instr):
        try:
            for name, kwargs in instr:
                print(name, kwargs)
                self._op_map[name](**kwargs)
        except TypeError:  # arguments wrong for some reason
            raise SyntaxError(instr)

    def _program_command(self, parent, func):
        sig = signature(func)
        cmd_options = sig.parameters
        cmd_name = func.__name__
        op_cmd = op_wait + cmd_name
        self._op_map[cmd_name] = func

        yield cmd_name, op_wait + parent, op_cmd

        if cmd_options:
            option_ctx = op_option + cmd_name
            for option_name, parameter in cmd_options.items():
                option_name = parameter.name
                store_ctx = op_store + option_name
                set_ctx = op_set + option_name

                yield option_token, op_cmd, option_ctx
                yield option_name, option_ctx, store_ctx

                yield set_token, store_ctx, set_ctx
                yield '*', set_ctx, 'NOTHANDLED EVER'
