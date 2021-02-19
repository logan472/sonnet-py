# Import core systems
import os, importlib, io, sys, time, glob, json

# Start Discord.py
import discord, asyncio

# Get token from environment variables.
TOKEN = os.environ.get('SONNET_TOKEN') or os.environ.get('RHEA_TOKEN')

# Initialize kernel workspace
sys.path.insert(1, os.getcwd() + '/cmds')
sys.path.insert(1, os.getcwd() + '/common')
sys.path.insert(1, os.getcwd() + '/libs')
sys.path.insert(1, os.getcwd() + '/dlibs')

intents = discord.Intents.default()
intents.typing = False
intents.presences = True
intents.guilds = True
intents.members = True
intents.reactions = True

# Initialise Discord Client.
Client = discord.Client(case_insensitive=True, status=discord.Status.online, intents=intents)


# Define ramfs
class ram_filesystem:
    def __init__(self):
        self.directory_table = {}
        self.data_table = {}

    def __enter__(self):
        return self

    def mkdir(self, make_dir):

        # Make fs list
        make_dir = make_dir.split("/")

        # If the current dir doesnt exist then create it
        if not (make_dir[0] in self.directory_table.keys()):
            self.directory_table[make_dir[0]] = ram_filesystem()

        # If there is more directory left then keep going
        if len(make_dir) > 1:
            return self.directory_table[make_dir[0]].mkdir("/".join(make_dir[1:]))
        else:
            return self

    def remove_f(self, remove_item):

        remove_item = remove_item.split("/")
        if len(remove_item) > 1:
            return self.directory_table[remove_item[0]].remove_f("/".join(remove_item[1:]))
        else:
            try:
                del self.data_table[remove_item[0]]
                return self
            except KeyError:
                raise FileNotFoundError("File does not exist")

    def read_f(self, file_to_open):

        file_to_open = file_to_open.split("/")
        try:
            if len(file_to_open) > 1:
                return self.directory_table[file_to_open[0]].read_f("/".join(file_to_open[1:]))
            else:
                return self.data_table[file_to_open[0]]
        except KeyError:
            raise FileNotFoundError("File does not exist")

    def create_f(self, file_to_write, f_type=io.BytesIO, f_args=[]):

        file_to_write = file_to_write.split("/")
        if len(file_to_write) > 1:
            try:
                return self.directory_table[file_to_write[0]].create_f("/".join(file_to_write[1:]), f_type=f_type, f_args=f_args)
            except KeyError:
                self.mkdir("/".join(file_to_write[:-1]))
                return self.directory_table[file_to_write[0]].create_f("/".join(file_to_write[1:]), f_type=f_type, f_args=f_args)
        else:
            self.data_table[file_to_write[0]] = f_type(*f_args)

        return self.data_table[file_to_write[0]]

    def rmdir(self, directory_to_delete):

        directory_to_delete = directory_to_delete.split("/")
        try:
            if len(directory_to_delete) > 1:
                self.directory_table[directory_to_delete[0]].rmdir("/".join(directory_to_delete[1:]))
            else:
                del self.directory_table[directory_to_delete[0]]
        except KeyError:
            raise FileNotFoundError("Folder does not exist")

    def ls(self, *folderpath):

        try:
            if folderpath:
                folderpath = folderpath[0].split("/")
                if len(folderpath) > 1:
                    return self.directory_table[folderpath[0]].ls("/".join(folderpath[1:]))
                else:
                    return self.directory_table[folderpath[0]].ls()
            else:
                return [list(self.data_table.keys()), list(self.directory_table.keys())]
        except KeyError:
            raise FileNotFoundError("Filepath does not exist")

    def tree(self, *folderpath):
        try:
            if folderpath:
                folderpath = folderpath[0].split("/")
                if len(folderpath) > 1:
                    return self.directory_table[folderpath[0]].tree("/".join(folderpath[1:]))
                else:
                    return self.directory_table[folderpath[0]].tree()
            else:
                datamap = [list(self.data_table.keys()), {}]
                for folder in self.directory_table.keys():
                    datamap[1][folder] = self.directory_table[folder].tree()
                return datamap

        except KeyError:
            raise FileNotFoundError("Filepath does not exist")


# Import blacklist
try:
    with open("common/blacklist.json", "r") as blacklist_file:
        blacklist = json.load(blacklist_file)
except FileNotFoundError:
    blacklist = {"guild": [], "user": []}
    with open("common/blacklist.json", "w") as blacklist_file:
        json.dump(blacklist, blacklist_file)

# Define debug commands

command_modules = []
command_modules_dict = {}
dynamiclib_modules = []
dynamiclib_modules_dict = {}

# Initalize ramfs, kernel ramfs
ramfs = ram_filesystem()
kernel_ramfs = ram_filesystem()


# Define kernel syntax error
class KernelSyntaxError(SyntaxError):
    pass


# Import configs
from LeXdPyK_conf import BOT_OWNER


def kernel_load_command_modules(*args):
    print("Loading Kernel Modules")
    # Globalize variables
    global command_modules, command_modules_dict, dynamiclib_modules, dynamiclib_modules_dict
    command_modules = []
    command_modules_dict = {}
    dynamiclib_modules = []
    dynamiclib_modules_dict = {}
    importlib.invalidate_caches()

    # Init return state
    err = []

    # Init imports
    for f in filter(lambda f: f.startswith("cmd_") and f.endswith(".py"), os.listdir('./cmds')):
        print(f)
        try:
            command_modules.append(importlib.import_module(f[:-3]))
        except Exception as e:
            err.append([e, f[:-3]])
    for f in filter(lambda f: f.startswith("dlib_") and f.endswith(".py"), os.listdir("./dlibs")):
        print(f)
        try:
            dynamiclib_modules.append(importlib.import_module(f[:-3]))
        except Exception as e:
            err.append([e, f[:-3]])

    # Update hashmaps
    for module in command_modules:
        try:
            command_modules_dict.update(module.commands)
        except AttributeError:
            err.append([KernelSyntaxError("Missing commands"), module.__name__])
    for module in dynamiclib_modules:
        try:
            dynamiclib_modules_dict.update(module.commands)
        except AttributeError:
            err.append([KernelSyntaxError("Missing commands"), module.__name__])

    if err: return ("\n".join([f"Error importing {i[1]}: {type(i[0]).__name__}: {i[0]}" for i in err]), [i[0] for i in err])


def regenerate_ramfs(*args):
    global ramfs
    ramfs = ram_filesystem()


def regenerate_kernel_ramfs(*args):
    global kernel_ramfs
    kernel_ramfs = ram_filesystem()


def kernel_reload_command_modules(*args):
    print("Reloading Kernel Modules")
    # Init vars
    global command_modules, command_modules_dict, dynamiclib_modules, dynamiclib_modules_dict
    command_modules_dict = {}
    dynamiclib_modules_dict = {}

    # Init ret state
    err = []

    # Update set
    for i in range(len(command_modules)):
        try:
            command_modules[i] = (importlib.reload(command_modules[i]))
        except Exception as e:
            err.append([e, command_modules[i].__name__])
    for i in range(len(dynamiclib_modules)):
        try:
            dynamiclib_modules[i] = (importlib.reload(dynamiclib_modules[i]))
        except Exception as e:
            err.append([e, dynamiclib_modules[i].__name__])

    # Update hashmaps
    for module in command_modules:
        try:
            command_modules_dict.update(module.commands)
        except AttributeError:
            err.append([KernelSyntaxError("Missing commands"), module.__name__])
    for module in dynamiclib_modules:
        try:
            dynamiclib_modules_dict.update(module.commands)
        except AttributeError:
            err.append([KernelSyntaxError("Missing commands"), module.__name__])

    # Regen tempramfs
    regenerate_ramfs()

    if err: return ("\n".join([f"Error reimporting {i[1]}: {type(i[0]).__name__}: {i[0]}" for i in err]), [i[0] for i in err])


def kernel_blacklist_guild(*args):

    blacklist["guild"].append(int(args[0][0]))
    with open("common/blacklist.json", "w") as blacklist_file:
        json.dump(blacklist, blacklist_file)


def kernel_blacklist_user(*args):

    blacklist["user"].append(int(args[0][0]))
    with open("common/blacklist.json", "w") as blacklist_file:
        json.dump(blacklist, blacklist_file)


def kernel_logout(*args):
    asyncio.create_task(Client.logout())


def kernel_drop_dlibs(*args):
    global dynamiclib_modules, dynamiclib_modules_dict
    dynamiclib_modules = []
    dynamiclib_modules_dict = {}


def kernel_drop_cmds(*args):
    global command_modules, command_modules_dict
    command_modules = []
    command_modules_dict = {}


# Generate debug command subset
debug_commands = {}
debug_commands["debug-add-guild-blacklist"] = kernel_blacklist_guild
debug_commands["debug-add-user-blacklist"] = kernel_blacklist_user
debug_commands["debug-modules-load"] = kernel_load_command_modules
debug_commands["debug-modules-reload"] = kernel_reload_command_modules
debug_commands["debug-logout-system"] = kernel_logout
debug_commands["debug-drop-ramfs"] = regenerate_ramfs
debug_commands["debug-drop-kramfs"] = regenerate_kernel_ramfs
debug_commands["debug-drop-modules"] = kernel_drop_dlibs
debug_commands["debug-drop-commands"] = kernel_drop_cmds

# Load command modules
if e := kernel_load_command_modules():
    print(e[0])


# A object used to pass error messages from the kernel callers to the event handlers
class errtype:
    def __init__(self, err, argtype):
        self.err = err
        self.errmsg = f"FATAL ERROR in {argtype}\nPlease contact <@!{BOT_OWNER}>"


# Catch errors.
@Client.event
async def on_error(event, *args, **kwargs):
    raise


async def event_call(argtype, *args):
    try:
        if argtype in dynamiclib_modules_dict.keys():
            await dynamiclib_modules_dict[argtype](
                *args,
                client=Client,
                ramfs=ramfs,
                bot_start=bot_start_time,
                command_modules=[command_modules, command_modules_dict],
                dynamiclib_modules=[dynamiclib_modules, dynamiclib_modules_dict],
                kernel_version=version_info,
                kernel_ramfs=kernel_ramfs
                )
    except Exception as e:
        return errtype(e, argtype)

    return None


@Client.event
async def on_connect():
    if e := await event_call("on-connect"):
        raise e.err


@Client.event
async def on_disconnect():
    if e := await event_call("on-disconnect"):
        raise e.err


@Client.event
async def on_ready():
    if e := await event_call("on-ready"):
        raise e.err


@Client.event
async def on_resumed():
    if e := await event_call("on-resumed"):
        raise e.err


@Client.event
async def on_message(message):
    static_args = message.content.split(" ")

    # If bot owner run a debug command
    if static_args[0] in debug_commands.keys() and BOT_OWNER and message.author.id == int(BOT_OWNER):
        if e := debug_commands[static_args[0]](static_args[1:]):
            await message.channel.send(e[0])
            raise e[1][0]
        else:
            await message.channel.send("Debug command returned no error status")
            return

    if e := await event_call("on-message", message):
        await message.channel.send(e.errmsg)
        raise e.err


@Client.event
async def on_message_delete(message):
    if e := await event_call("on-message-delete", message):
        await message.channel.send(e.errmsg)
        raise e.err


@Client.event
async def on_bulk_message_delete(messages):
    if e := await event_call("on-bulk-message-delete", messages):
        await messages[0].channel.send(e.errmsg)
        raise e.err


@Client.event
async def on_raw_message_delete(payload):
    if e := await event_call("on-raw-message-delete", payload):
        await Client.get_channel(payload.channel_id).send(e.errmsg)
        raise e.err


@Client.event
async def on_raw_bulk_message_delete(payload):
    if e := await event_call("on-raw-bulk-message-delete", payload):
        await Client.get_channel(payload.channel_id).send(e.errmsg)
        raise e.err


@Client.event
async def on_message_edit(old_message, message):
    if e := await event_call("on-message-edit", old_message, message):
        await message.channel.send(e.errmsg)
        raise e.err


@Client.event
async def on_raw_message_edit(payload):
    if e := await event_call("on-raw-message-edit", payload):
        await Client.get_channel(payload.channel_id).send(e.errmsg)
        raise e.err


@Client.event
async def on_reaction_add(reaction, user):
    if e := await event_call("on-reaction-add", reaction, user):
        await reaction.message.channel.send(e.errmsg)
        raise e.err


@Client.event
async def on_raw_reaction_add(payload):
    if e := await event_call("on-raw-reaction-add", payload):
        await Client.get_channel(payload.channel_id).send(e.errmsg)
        raise e.err


@Client.event
async def on_reaction_remove(reaction, user):
    if e := await event_call("on-reaction-remove", reaction, user):
        await reaction.message.channel.send(e.errmsg)
        raise e.err


@Client.event
async def on_raw_reaction_remove(payload):
    if e := await event_call("on-raw-reaction-remove", payload):
        await Client.get_channel(payload.channel_id).send(e.errmsg)
        raise e.err


@Client.event
async def on_reaction_clear(message, reactions):
    if e := await event_call("on-reaction-clear", message, reactions):
        await message.channel.send(e.errmsg)
        raise e.err


@Client.event
async def on_raw_reaction_clear(payload):
    if e := await event_call("on-raw-reaction-clear", payload):
        await Client.get_channel(payload.channel_id).send(e.errmsg)
        raise e.err


@Client.event
async def on_reaction_clear_emoji(reaction):
    if e := await event_call("on-reaction-clear-emoji", reaction):
        await reaction.message.channel.send(e.errmsg)
        raise e.err


@Client.event
async def on_raw_reaction_clear_emoji(payload):
    if e := await event_call("on-raw-reaction-clear-emoji", payload):
        await Client.get_channel(payload.channel_id).send(e.errmsg)
        raise e.err


@Client.event
async def on_member_join(member):
    if e := await event_call("on-member-join", member):
        raise e.err


@Client.event
async def on_member_remove(member):
    if e := await event_call("on-member-remove", member):
        raise e.err


@Client.event
async def on_member_update(before, after):
    if e := await event_call("on-member-update", before, after):
        raise e.err


@Client.event
async def on_guild_join(guild):
    if e := await event_call("on-guild-join", guild):
        raise e.err


@Client.event
async def on_guild_remove(guild):
    if e := await event_call("on-guild-remove", guild):
        raise e.err


@Client.event
async def on_guild_update(before, after):
    if e := await event_call("on-guild-update", before, after):
        raise e.err


@Client.event
async def on_member_ban(guild, user):
    if e := await event_call("on-member-ban", guild, user):
        raise e.err


@Client.event
async def on_member_unban(guild, user):
    if e := await event_call("on-member-unban", guild, user):
        raise e.err


version_info = "LeXdPyK 1.2-DEV"
bot_start_time = time.time()
if TOKEN:
    Client.run(TOKEN, bot=True, reconnect=True)
else:
    print("You need a token set in SONNET_TOKEN or RHEA_TOKEN environment variables to use sonnet")

# Clear cache at exit
for i in glob.glob("datastore/*.cache.db"):
    os.remove(i)
print("\rCache Cleared, Thank you for Using Sonnet")
