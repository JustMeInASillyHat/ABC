from __future__ import annotations

import os
import re
from time import sleep
import pandas as pd
import json
# https://github.com/JustMeInASillyHat/ABC

# Note: A more complete reset system would be necessary for some dialogue to make more sense!

PLOT_EVENTS = []
COMMANDS = []
LOCATIONS = []
NPCs = []
ITEMS = []
INVENTORY = []

PET = "pet"
TALK = "talk"
GIVE = "give"
GO = "go"
PICK_UP = "pick up"


class NPC:
    def __init__(self, name, displayname, aliases):
        self.name: str = name
        self.displayname = displayname
        if aliases:
            self.aliases = aliases.split(", ")
        else:
            self.aliases = []
        self.aliases.append(name)
        self.aliases.append(displayname)
        self.commands_issued = {}


class Item:
    def __init__(self, name, displayname, aliases, description, is_NPC, quantity_left, acquire_condition):
        self.name: str = name
        self.displayname: str = displayname
        if aliases:
            self.aliases = aliases.split(", ")
        else:
            self.aliases = []
        self.aliases.append(name)
        self.aliases.append(displayname)
        self.description: str = description
        self.is_NPC: bool = is_NPC
        self.quantity_left = int(quantity_left)
        self.acquire_condition = acquire_condition
        self.inventory_number: int = 0


class Location:
    def __init__(self, name, displayname, aliases, locked, first_entrance_description, standard_entrance_description,
                 locations_within_reach, NPCs_present=None):
        self.name = name
        self.displayname = displayname
        if aliases:
            self.aliases = aliases.split(", ")
        else:
            self.aliases = []
        self.aliases.append(name)
        self.aliases.append(displayname)
        self.locked = locked
        self.first_entrance_description = first_entrance_description
        self.standard_entrance_description = standard_entrance_description
        self.locations_within_reach = locations_within_reach.split(", ")
        self.entered: bool = False
        if NPCs_present:
            self.NPCs_present = NPCs_present.split(", ")
            if isinstance(self.NPCs_present, str):
                self.NPCs_present = list(self.NPCs_present)
        else:
            self.NPCs_present = []


class State:
    def __init__(self, name, reset_value, reset_type, repeat):
        self.name = name
        self.active = False
        self.reset_value = reset_value
        self.reset_type = reset_type
        self.repeat = repeat
        self.current_reset_value = 0


class Command:
    def __init__(self, name: str):
        self.name = name
        try:
            self.table = pd.read_excel(MASTER_FILE, name, dtype=str, na_values=["nan"], keep_default_na=False)
        except ValueError:
            pass


def fetch_valid_targets(location, command):
    desired_number = 1
    if command.name == PET:
        df = pd.read_excel(MASTER_FILE, "pet", dtype=str, na_values=["nan"], keep_default_na=False)
        valid_targets = list(filter(lambda npc: npc.name in list(df.target.unique()), location.NPCs_present))
    elif command.name == TALK:
        valid_targets = location.NPCs_present
    elif command.name == GO:
        valid_targets = location.locations_within_reach
    elif command.name == GIVE:
        valid_targets = location.NPCs_present + INVENTORY
        desired_number = 2
    elif command.name == PICK_UP:
        df = pd.read_excel(MASTER_FILE, "pick up", dtype=str, na_values=["nan"], keep_default_na=False)
        valid_targets = list(filter(lambda npc: npc.name in list(df.target.unique()), location.NPCs_present))
    else:
        raise Exception("This command isn't recognised by fetch_valid_targets")
    return valid_targets, desired_number


def list_commands(location: Location):
    print(f"⭐ Current location: {location.displayname}")
    print(
        f"⭐ Locations reachable from here: {[location.displayname for location in location.locations_within_reach]}")
    print("    ⭐ Type \"go to <location>\" to approach any of the above.")
    print("    ⭐ HINT: Type \"alias <object>\" to discover easier ways to reference a character, location, or item")
    if location.NPCs_present:
        print("⭐ Interactions available:")
        for npc in location.NPCs_present:
            actions = []
            for action in [TALK, PET, PICK_UP, GIVE]:
                if npc.name in list(pd.read_excel(MASTER_FILE, action, dtype=str).target.unique()):
                    actions.append(action)
            if GIVE in actions:
                actions.remove(GIVE)
                if len(INVENTORY) > 0:
                    actions.append("give <item>")
            print(f"    ⭐ {npc.displayname} {actions}")
    if len(INVENTORY) > 0:
        print(f"⭐ Inventory:")
        for item in INVENTORY:
            print(f"    ⭐ {item.inventory_number}x {item.displayname}: {item.description}")


def condition_met(condition):
    if not condition:
        return True
    try:
        if list(filter(lambda event: event.name == condition, PLOT_EVENTS))[0].active:
            return True
        else:
            return False
    except IndexError:
        if condition in [item.name for item in INVENTORY]:
            return True
        else:
            return False


def add_inventory(location: Location, item: Item):
    if item.quantity_left > 0 and condition_met(item.acquire_condition):
        if item not in INVENTORY:
            INVENTORY.append(item)
        item.inventory_number += 1
        item.quantity_left -= 1
        if item.name == "skelekitty":
            list(filter(lambda loc: loc.name == "main", LOCATIONS))[0].locked = "A six-armed waitress stops you at " \
                                                                                "the door. \"I'm sorry,\" she says, " \
                                                                                "indicating the skelekitty you are " \
                                                                                "holding. \"No pets allowed. Unless " \
                                                                                "this is your " \
                                                                                "familiar?\"\n\"...\"\n\"I see, " \
                                                                                "in that case, I'm afraid we can't " \
                                                                                "let you bring it inside.\" "
        elif item.name == "key":
            list(filter(lambda loc: loc.name == "back", LOCATIONS))[0].locked = False
        elif item.name == "tooth":
            display(
                "As the skelekitty rubs its head against your hand affectionately, you see your chance to pocket one "
                "of its fangs.")
            if action_confirm("take it"):
                display("You dislodge the tooth carefully: The skelekitty hardly seems to "
                        "notice, and carries on purring.")
            else:
                display("You give the skelekitty a friendly scrooch.")
        elif item.name == "awl":
            display("You ask Shemeshka for the tooth back, and she obliges, before issuing her default dialogue:")
        elif item.name == "apron":
            if action_confirm("put the apron on now"):
                list(filter(lambda x: x.name == "apron_donned", PLOT_EVENTS))[0].active = True
                display("You put on the apron!")
                INVENTORY.remove(list(filter(lambda item: item.name == "apron", INVENTORY))[0])
                item.inventory_number = 0
            else:
                display("You do not put on the apron...")
        if item.quantity_left == 0:
            if not item.is_NPC and item in location.NPCs_present:  # if the item object has been added directly to this I guess??
                location.NPCs_present.remove(item)
            elif item.is_NPC:
                location.NPCs_present.remove(list(filter(lambda char: char.name == item.is_NPC, NPCs))[0])


def trigger_plot_event(state_trigger):
    for event in PLOT_EVENTS:
        if event.name == state_trigger:
            event.active = True
            event.current_reset_value = 0
    if state_trigger == "kid_cat":
        list(filter(lambda loc: loc.name == "main", LOCATIONS))[0].locked = False
        list(filter(lambda loc: loc.name == "front", LOCATIONS))[0].NPCs_present.append(
            list(filter(lambda npc: npc.name == "skelekitty", NPCs))[0])
    if state_trigger == "tooth_returned":
        list(filter(lambda i: i.name == "tooth", ITEMS))[0].quantity_left += 1


def event_reset(type):
    for event in PLOT_EVENTS:
        if event.reset_type == type:
            if event.active:
                if not event.reset_value:
                    return
                else:
                    event.current_reset_value += 1
        if event.current_reset_value == event.reset_value:
            event.active = False
            event.current_reset_value = 0


def action_confirm(action: str):
    display(f"Would you like to {action}?")
    if input(">>> ") == "Y" or "y" or "yes" or "Yes" or "sure" or "OK" or "ok" or "okay":
        return True
    else:
        return False


def go_oc():
    display(f"{PLAYER_NAME}?")
    input(">>> ")
    sleep(1)
    display(OC_RESPONSES[0])
    input(">>> ")
    sleep(1)
    display(OC_RESPONSES[1])
    input(">>> ")
    sleep(1)
    display("With that, you find yourself transported back IC...")


def command_override(command, target, item=False):
    if item:
        key = item.name
    else:
        key = command.name
    for event in list(filter(lambda x: x.active, PLOT_EVENTS)):
        try:
            display(otd_dict[event.name][key][target.name])
            return True
        except KeyError:
            for inventory_item in INVENTORY:
                try:
                    display(otd_dict[inventory_item.name][key][target.name])
                    return True
                except KeyError:
                    pass
    return False


def fetch_first_time_command(command: Command, target: NPC):
    target_mask = command.table["target"] == target.name
    state_triggers = command.table[target_mask].iloc[0]["state_triggers"]
    if state_triggers:
        state_triggers = state_triggers.split(", ")
    target.commands_issued[command] = True
    try:
        trigger_on_first = command.table[target_mask].iloc[0]["trigger_on_first"]
        if trigger_on_first:
            trigger_on_first = trigger_on_first.split(", ")
    except KeyError:
        trigger_on_first = True
    if trigger_on_first and state_triggers:
        for trigger in state_triggers:
            if trigger in trigger_on_first:
                trigger_plot_event(trigger)
    try:
        return command.table[target_mask].iloc[0]["first"]
    except KeyError:
        return None


def execute_command(command: Command, target: NPC, location: Location):
    target_mask = command.table["target"] == target.name
    state_triggers = command.table[target_mask].iloc[0]["state_triggers"]
    if state_triggers:
        state_triggers = state_triggers.split(", ")
    item = command.table[target_mask].iloc[0]["item"]
    output = None  # this looks clunky but I previously used returns and this was the only way to stack item add
    # blurbs correctly

    # state overrides take precedent over first time dialogues
    if command_override(command, target):
        pass
    elif not target.commands_issued[command]:
        first_time_output = fetch_first_time_command(command, target)
        target.commands_issued[command] = True
        if first_time_output is not None:
            output = first_time_output
        else:
            output = command.table[target_mask].iloc[0]["default"]
    else:
        output = command.table[target_mask].iloc[0]["default"]
    if output is not None:
        display(output)
    if state_triggers:
        for trigger in state_triggers:
            trigger_plot_event(trigger)
    if item:
        try:
            add_inventory(location, list(filter(lambda i: i.name == item, ITEMS))[0])
        except IndexError:
            print(f"Error: No item object with name {item} found!")


def go(current_location, destination: Location):
    event_reset("door")
    if destination.name == "oc":
        go_oc()
    if destination.locked:
        display(destination.locked)
        return current_location
    else:
        if destination.entered:
            display(destination.standard_entrance_description)
        else:
            if destination.first_entrance_description:
                display(destination.first_entrance_description)
            else:
                display(destination.standard_entrance_description)
            destination.entered = True
        if destination.name == "oc":
            return current_location
        return destination


def give(npc, item, location: Location):
    table = pd.read_excel(MASTER_FILE, "give", dtype=str, na_values=["nan"], keep_default_na=False)
    npc_mask = table["target"] == npc.name
    item_mask = table["item"] == item.name
    output = None
    state_triggers = table[npc_mask & item_mask].iloc[0]["state_triggers"]
    if state_triggers:
        state_triggers = state_triggers.split(", ")
    item_exchange = table[npc_mask & item_mask].iloc[0]["item_exchange"]
    for state_trigger in state_triggers:
        trigger_plot_event(state_trigger)
    if item_exchange:
        add_inventory(location, list(filter(lambda x: x.name == item_exchange, ITEMS))[0])

    if not table[npc_mask & item_mask].iloc[0]["stay_in_inventory"]:
        item.inventory_number -= 1
    if item.inventory_number == 0:
        INVENTORY.remove(item)

    if command_override(list(filter(lambda c: c.name == GIVE, COMMANDS))[0], npc, item):
        pass
    else:
        output = table[npc_mask & item_mask].iloc[0]["response"]
    if output is not None:
        display(output)


def no_command():
    display("You did not specify a valid command!")


def invalid_target():
    display("You did not specify a valid target!")


def too_many_commands():
    display("You entered more than one command!")


def no_target():
    display("You did not specify a valid target.")


def too_many_targets():
    display("You listed too many targets!")


def missing_NPC():
    display("You did not specify a valid NPC to give this to")


def missing_item():
    display("You did not specify a valid item!")


def item_not_in_inventory(item):
    display(f"You couldn't find any {item} in your inventory!")


def out_of_reach():
    display(f"You can't reach that from here!")


def already_there():
    display("You're already there!")


def parse_input(raw_input, location):
    targets = []
    commands_mentioned = []
    current_location = location

    if raw_input == "?":
        list_commands(location)
    elif raw_input.startswith("alias "):
        checkall = location.NPCs_present + location.locations_within_reach + INVENTORY
        for object in checkall:
            for alias in object.aliases:
                if raw_input.endswith(alias):
                    display(f"{object.name}: {[alias.lower() for alias in object.aliases]}")
                    return current_location
                if checkall.index(object) == len(checkall) - 1:
                    display(f"No aliases for {raw_input[6:]} can be found at this time")
                    return current_location
    else:
        for command in COMMANDS:
            if re.search(command.name, raw_input):
                commands_mentioned.append(command)
        if len(commands_mentioned) == 0:
            no_command()
        elif len(commands_mentioned) > 1:
            too_many_commands()
        else:
            command = commands_mentioned[0]
            valid_targets, desired_number = fetch_valid_targets(location, command)
            for item in valid_targets:
                for alias in item.aliases:
                    if re.search(alias, raw_input, re.IGNORECASE) is not None:
                        if item not in targets:
                            targets.append(item)
                        continue
            for target in targets:
                try:
                    if target.is_NPC and len(list(filter(lambda x: x.name == target.name, targets))) > 1:
                        targets.remove(target)
                except AttributeError:
                    pass
            if len(targets) == 0:
                if command.name == "go":
                    for alias in current_location.aliases:
                        if raw_input.find(alias) != -1:
                            already_there()
                            return current_location
                    for x in LOCATIONS:
                        for alias in x.aliases:
                            if raw_input.find(alias) != -1:
                                out_of_reach()
                                return current_location
                else:
                    no_target()
            elif len(targets) == desired_number:
                if command.name == GIVE:
                    if targets[0] in INVENTORY and targets[1] in NPCs:
                        give(targets[1], targets[0], location)
                    elif targets[0] in NPCs and targets[1] in INVENTORY:
                        give(targets[0], targets[1], location)
                elif command.name == GO:
                    current_location = go(current_location, targets[0])
                else:
                    execute_command(command, targets[0], location)
            elif len(targets) > desired_number:
                too_many_targets()
            else:
                if targets[0] in ITEMS:
                    missing_NPC()
                elif targets[0] in NPCs:
                    known_item = False
                    for item in ITEMS:
                        for alias in item.aliases:
                            if re.search(alias, raw_input):
                                item_not_in_inventory(alias)
                                known_item = True
                                continue
                    if not known_item:
                        missing_item()
                else:
                    invalid_target()
    return current_location


def display(message):
    if DEBUG:
        print(message)
    else:
        regex = re.compile(">\S.*\S<")
        for instance in regex.findall(message):
            new = instance.replace(">", "\033[1m")
            new = new.replace("<", "\033[0m")
            message = message.replace(instance, new)

        for char in message:
            sleep(0.05)
            print(char, end='', flush=True)
        print()


def setup():
    mode = input("Please enter your name to proceed:\n")
    if mode == "debug":
        print("Which excel file would you like to use?")
        excel_files = []
        for item in os.listdir():
            if item.endswith(".xlsx"):
                print(f"- {item}")
                excel_files.append(item)
        excel_file = ""
        while excel_file not in excel_files:
            excel_file = input(">>> ")

        print("Which json file would you like to use?")
        json_files = []
        for item in os.listdir():
            if item.endswith(".json"):
                print(f"- {item}")
                json_files.append(item)
        json_file = ""
        while json_file not in json_files:
            json_file = input(">>> ")
        return True, "Sophia", ["How are you doing?", "Thanks for debugging the game!"], excel_file, json_file
    elif mode == "Conor":
        return False, "Conor", ["I really love you", "Thanks for helping me learn how to code <3"], "ABC_OG.xlsx", "otd_og.json"
    else:
        return False, mode, ["Thank you for playing my game", "How are you finding it so far?"], "ABC_PG.xlsx", "otd_pg.json"


def main():
    global DEBUG, PLAYER_NAME, OC_RESPONSES, MASTER_FILE
    DEBUG, PLAYER_NAME, OC_RESPONSES, MASTER_FILE, OTD_FILE = setup()

    with open(OTD_FILE, "r") as f:
        global otd_dict
        otd_dict = json.load(f)

    for command in [PET, TALK, GO, GIVE, PICK_UP]:
        COMMANDS.append(Command(command))

    location_table = pd.read_excel(MASTER_FILE, "location_data", dtype=str, na_values=["nan"],
                                   keep_default_na=False)
    for location in [Location(**location_data) for index, location_data in location_table.iterrows()]:
        LOCATIONS.append(location)

    NPC_table = pd.read_excel(MASTER_FILE, "character_data", dtype=str, na_values=["nan"], keep_default_na=False)
    for npc in [NPC(**NPC_data) for index, NPC_data in NPC_table.iterrows()]:
        NPCs.append(npc)

    item_table = pd.read_excel(MASTER_FILE, "item_data", dtype=str, na_values=["nan"], keep_default_na=False)
    for item in [Item(**item_data) for index, item_data in item_table.iterrows()]:
        ITEMS.append(item)
        # INVENTORY.append(item)  # (for debug purposes)
        # item.inventory_number +=1 # (for debug purposes)

    state_table = pd.read_excel(MASTER_FILE, "state_data", dtype=str, na_values=["nan"], keep_default_na=False)
    for event in [State(**state_data) for index, state_data in state_table.iterrows()]:
        PLOT_EVENTS.append(event)

    for npc in NPCs:
        for command in COMMANDS:
            npc.commands_issued[command] = False

    for x in LOCATIONS:
        temp_list = []
        for item in x.NPCs_present:
            temp_list += list(filter(lambda npc: npc.name == item, NPCs))
        x.NPCs_present = temp_list
        temp_list = []
        for item in x.locations_within_reach:
            temp_list += list(filter(lambda loc: loc.name == item, LOCATIONS))
        x.locations_within_reach = temp_list

    current_location = list(filter(lambda location: location.name == "front", LOCATIONS))[0]
    display(current_location.first_entrance_description)
    current_location.entered = True
    if not DEBUG:
        display("⭐ HINT: type \"?\" to see available actions")
    while True:
        raw_input = input(">>> ")
        current_location = parse_input(raw_input, current_location)


if __name__ == "__main__":
    main()
