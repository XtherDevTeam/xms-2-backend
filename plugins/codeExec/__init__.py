import plugins.codeExec.handlers as handlers

def registry():
    return {
        'name': 'rce',
        'description': 'run shell script remotely',
        'avaliablePremissionLevel': 1
    }    