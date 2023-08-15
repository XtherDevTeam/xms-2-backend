import plugins.spotdlBackend.handlers as handlers

def registry():
    return {
        'name': 'spotdlBackend',
        'description': 'download music with spotdl',
        'avaliablepermissionLevel': 1
    }    