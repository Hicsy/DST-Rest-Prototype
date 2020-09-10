# A quick app for command queueing. Mostly RESTful.
# StyleGuide loosely observed: https://google.github.io/styleguide/pyguide.html
# HTTP Status Codes: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status
import sys
from datetime import datetime
from bottle import run, route, get, post, request, put, response, static_file

print("-------------")
print("API Reloaded!")
print("-------------")

################ Configurable App Defaults ##############
# Change any options here to set as your app defaults:
default_server = 'MyDediServer'
api_host = "0.0.0.0"
api_port = "10777"
api_reloader = False
######



################ Initialisation ##############
servers = []
truthy = ['true', 't', 'yes', 'y', 'on', '1']
falsy = ['false', 'f', 'no', 'n', 'off', '0']
# Checking for input parameters which override the above defaults
arg_index = 1
arg_count = len(sys.argv) # includes arg0 which is the name of the script!
while ( arg_index < arg_count ):
    my_arg = sys.argv[arg_index]
    next_arg = sys.argv[arg_index+1] if arg_index+1 < arg_count else None
    print ("Parameter %i: %s" % (arg_index, my_arg))
    if my_arg.lower().startswith('--server=')==True:
        default_server = my_arg[9:]
    elif my_arg.lower()=='--server':
        if next_arg is not None: default_server = next_arg
    if my_arg.lower().startswith('--host=')==True:
        api_host = my_arg[7:]
    elif my_arg.lower()=='--host':
        if next_arg is not None: api_host = next_arg
    if my_arg.lower().startswith('--port=')==True:
        api_port = my_arg[7:]
    elif my_arg.lower()=='--port':
        if next_arg is not None: api_port = next_arg
    if my_arg.lower().startswith('--reload=')==True:
        api_reloader = my_arg[9:].lower() not in falsy
    elif my_arg.lower() == '--reload':
        if next_arg is not None:
            api_reloader = next_arg.lower() not in falsy
    elif my_arg.lower() == '-r':
        api_reloader = True
    arg_index = arg_index+1

print('Default server selected: '+ default_server)
print('Api Listener host interface: '+ api_host)
print('API Port: '+ api_port)
print('Auto-Reloader : '+ str(api_reloader))
################



################ Helper Functions ##############
def get_server(server_name):
    my_server = next((server for server in servers if server['name'] == server_name), None)
    return my_server

def get_shard(server_name, shard_id):
    my_server = get_server(server_name)
    if my_server is None:
        return None
    else:
        my_shard = next((shard for shard in my_server['shards'] if shard['id'] == shard_id), None)
        return my_shard

# TODO: Python ppl say "choose returning a list or just 1 item, not both"
def get_command(server_name, shard_id, command_id, command_status):
    my_shard = get_shard(server_name, shard_id)
    if my_shard is None:
        my_command = None
    else:
        if command_id is None: # then get a list
            my_commands = []
            if command_status is None:
                my_commands = my_shard['commands']
            else:
                my_commands = [command for command in my_shard['commands'] if command['status'].lower() == command_status.lower()]
            return my_commands
        else: # then return the single specified command
            my_command = next((command for command in my_shard['commands'] if command['id'] == command_id), None)
    return my_command

def new_server(server_name):
    my_server = {'name': server_name, 'shards': []}
    servers.append(my_server)
    return my_server

def new_shard(server_name, shard_id):
    my_shard = get_shard(server_name, shard_id)
    if my_shard is None:
        my_server = get_server(server_name)
        if my_server is None: my_server = new_server(server_name)
        my_commands = [{'id': 0, 'command': 'start', 'status': "New"}]
        my_shard = {'id': shard_id, 'commands': my_commands}
        my_server['shards'].append(my_shard)
    return my_shard

def new_command(server_name=None, shard_id=None, command="test"):
    my_status = 418
    def add_command(shard, rpc):
        my_command = {
            'id': len(shard['commands']),
            'command': rpc,
            'status': "New"}
        shard['commands'].append(my_command)
        return 201
    
    if server_name is None:
        # Send command to all servers.
        for my_server in servers:
            if my_status == 418: my_status = 503
            for my_shard in my_server['shards']:
                my_status = add_command(my_shard, command)
    elif shard_id is None:
        # Send command to all shards within server.
        my_server = get_server(server_name)
        if my_server is not None:
            if my_status == 418: my_status = 503
            for my_shard in my_server['shards']:
                my_status = add_command(my_shard, command)
    else:
        # Send command to specific shard.
        my_shard = get_shard(server_name, shard_id)
        if my_shard is not None:
            my_status = 503
            my_status = add_command(my_shard, command)
    return my_status
################



################ Quick Commands ##############
# Some extra (non-RESTful) functions for quick-commands in lieu of a web frontend.
def quick_revive(player_name=None):
    my_status = 418
    if player_name:
        my_rpc = ('UserToPlayer("%s"):'
                  'PushEvent("respawnfromghost")') %(player_name)
    else:
        my_rpc = ('for k,v in pairs(AllPlayers) do '
                  'v:PushEvent("respawnfromghost") end')
    my_status = new_command(None, None, my_rpc)
    return my_status

def quick_give(player_name=None, item="perogies", item_count=10):
    if item_count is None: item_count = 10
    my_status = 418
    if player_name:
        my_rpc = ('c_select(UserToPlayer("%s")) '
                  'c_give("%s",%i)') %(player_name, item, int(item_count))
    else:
        my_rpc = ('for k,v in pairs(AllPlayers) do '
                  'c_select(v) c_give("%s",%i}) end') %(item, int(item_count))
    my_status = new_command(None, None, my_rpc)
    return my_status
################



################ GET/POST WWW ###############
# Quickly "Post" a new command by opening a web-page (not RESTful)
@get('/quick/<my_cmd>')
@get('/quick/<my_cmd>/<my_var>')
@get('/quick/<my_cmd>/<my_var>/<my_option>')
@get('/quick/<my_cmd>/<my_var>/<my_option>/<my_modifier>')
def post_quick_command(my_cmd,my_var=None,my_option=None, my_modifier=None):
    response.status = 501
    my_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if my_cmd.lower() == "revive":
        response.status = quick_revive(my_var)
    elif my_cmd.lower() == "give":
        response.status = quick_give(my_var, my_option, my_modifier)
    
    my_response = "<h1>{}</h1><br>{}".format(response.status, my_time)
    return my_response
################



################ GET ##############
# Shaddup Favicon alert!
@route('/favicon.ico', method='GET')
def get_favicon():
    return static_file('favicon.ico', root='./static/')
    #response.status = 204
    #return

# List Servers
@get('/servers')
def get_servers_list():
    return {'servers': servers}

# Detail Server
@get('/servers/<server_name>')
def get_server_details(server_name):
    my_server = get_server(server_name)
    if my_server is None:
        response.status = 404
        return {}
    else:
        return {'server': my_server}

# List Commands (can be filtered for unresolved). TODO: Handle more filtering?
@get('/servers/<server_name>/<shard_id>/commands')
def get_pending_commands(server_name,shard_id):
    status_filter = request.params.get('status')
    my_commands = get_command(server_name, shard_id, None, status_filter)
    if my_commands:
        for cmd in my_commands: cmd['status'] = 'Sent'
        return {'commands': my_commands}
################



################ POST ###############
# Post a new server listing by Name
@post('/servers')
def post_server():
    my_name = request.json.get('name')
    new_server(my_name)
    response.status = 201
    return response

# Post new commands.
@post('/servers/<server_name>/commands')
@post('/servers/<server_name>/<shard_id>/commands')
def post_command(server_name, shard_id=None):
    my_command = request.json.get('command')
    if my_command is None:
        return 400
    else:
        if server_name == 'default': server_name = default_server
        response.status = new_command(server_name, shard_id, my_command)
        return response
################



############### PATCH ################
# Update pending commands.
@post('/servers/<server_name>/<shard_id>/commands/<cmd_id:int>')
def patch_command(server_name, shard_id, cmd_id):
    data = request.json #.get('data')
    if data is None:
        response.status = 400
        return
    else:
        my_command = get_command(server_name, shard_id, cmd_id, None)
        if my_command is None:
            response.status = 404
            return
        else:
            my_command['status'] = data['status']
            response.status = 204
            return

# PUT server status. Return [201] if new server created.
@post('/servers/<server_name>/<shard_id>')
def put_server(server_name,shard_id):
    data = request.json #.get('data')
    if data is None:
        response.status = 400
        return
    my_shard = get_shard(server_name, shard_id)
    if my_shard is None:
        my_shard = new_shard(server_name, shard_id)
        response.status = 201
    else:
        response.status = 204
    # TODO: put a k,v iteration here instead!
    my_shard['settings'] = data['settings']
    my_shard['mods'] = data['mods']
    my_shard['world'] = data['world']
    my_shard['statevars'] = data['statevars']
    my_shard['players'] = data['players']
    # return {'server' : myServer}
    return "OK"
################



if __name__ == "__main__":
    run(reloader=api_reloader, host=api_host, port=api_port)
