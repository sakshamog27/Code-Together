"""
DUNGEON QUEST
A text-based RPG adventure game.

Features:
- Character creation with classes (Warrior, Mage, Rogue)
- Turn-based combat with critical hits, dodging, and special abilities
- Inventory & equipment system (weapons, armor, potions)
- Leveling system with experience points
- Multiple explorable rooms/map with random encounters
- A shop to buy/sell items
- A boss fight at the end
- Save and load game progress (JSON)
"""

import random
import json
import os
import sys
import time

SAVE_FILE = "savegame.json"


# --------------------------------------------------------------------------
# UTILITY FUNCTIONS
# --------------------------------------------------------------------------

def slow_print(text, delay=0.015):
    """Print text with a slight typewriter effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def divider():
    print("-" * 50)


def press_enter():
    input("\nPress Enter to continue...")


# --------------------------------------------------------------------------
# ITEM SYSTEM
# --------------------------------------------------------------------------

class Item:
    def __init__(self, name, item_type, value, price):
        self.name = name
        self.item_type = item_type  # 'weapon', 'armor', 'potion'
        self.value = value          # damage / defense / heal amount
        self.price = price

    def to_dict(self):
        return self.__dict__

    @staticmethod
    def from_dict(d):
        return Item(d["name"], d["item_type"], d["value"], d["price"])

    def __str__(self):
        if self.item_type == "weapon":
            return f"{self.name} (+{self.value} ATK) - {self.price}g"
        elif self.item_type == "armor":
            return f"{self.name} (+{self.value} DEF) - {self.price}g"
        elif self.item_type == "potion":
            return f"{self.name} (Heals {self.value} HP) - {self.price}g"
        return self.name


# Predefined item pool
SHOP_ITEMS = [
    Item("Iron Sword", "weapon", 8, 50),
    Item("Steel Axe", "weapon", 14, 90),
    Item("Enchanted Blade", "weapon", 22, 160),
    Item("Leather Armor", "armor", 5, 40),
    Item("Chainmail", "armor", 10, 85),
    Item("Plate Armor", "armor", 18, 150),
    Item("Health Potion", "potion", 25, 20),
    Item("Greater Potion", "potion", 60, 45),
]


# --------------------------------------------------------------------------
# CHARACTER CLASSES
# --------------------------------------------------------------------------

class Character:
    def __init__(self, name, hp, attack, defense):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.attack = attack
        self.defense = defense
        self.alive = True

    def is_alive(self):
        return self.hp > 0

    def take_damage(self, amount):
        actual = max(1, amount - self.defense)
        self.hp -= actual
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
        return actual

    def heal(self, amount):
        self.hp = min(self.max_hp, self.hp + amount)


class Player(Character):
    CLASS_STATS = {
        "Warrior": {"hp": 120, "attack": 14, "defense": 8, "crit": 0.15},
        "Mage":    {"hp": 80,  "attack": 20, "defense": 4, "crit": 0.10},
        "Rogue":   {"hp": 95,  "attack": 17, "defense": 5, "crit": 0.30},
    }

    def __init__(self, name, char_class):
        stats = self.CLASS_STATS[char_class]
        super().__init__(name, stats["hp"], stats["attack"], stats["defense"])
        self.char_class = char_class
        self.crit_chance = stats["crit"]
        self.level = 1
        self.xp = 0
        self.xp_to_next = 100
        self.gold = 100
        self.inventory = []
        self.equipped_weapon = None
        self.equipped_armor = None

    def total_attack(self):
        bonus = self.equipped_weapon.value if self.equipped_weapon else 0
        return self.attack + bonus

    def total_defense(self):
        bonus = self.equipped_armor.value if self.equipped_armor else 0
        return self.defense + bonus

    def gain_xp(self, amount):
        self.xp += amount
        slow_print(f"You gained {amount} XP!")
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level_up()

    def level_up(self):
        self.level += 1
        self.max_hp += 20
        self.hp = self.max_hp
        self.attack += 4
        self.defense += 2
        self.xp_to_next = int(self.xp_to_next * 1.4)
        slow_print(f"*** LEVEL UP! You are now level {self.level}! ***")

    def add_item(self, item):
        self.inventory.append(item)

    def equip(self, item):
        if item.item_type == "weapon":
            self.equipped_weapon = item
            slow_print(f"You equipped {item.name}.")
        elif item.item_type == "armor":
            self.equipped_armor = item
            slow_print(f"You equipped {item.name}.")
        else:
            print("You can't equip that.")

    def use_potion(self, item):
        if item.item_type != "potion":
            print("That's not a potion.")
            return False
        self.heal(item.value)
        self.inventory.remove(item)
        slow_print(f"You drink the {item.name} and recover {item.value} HP!")
        return True

    def status(self):
        divider()
        print(f"{self.name} the {self.char_class} | Lv.{self.level}")
        print(f"HP: {self.hp}/{self.max_hp}  ATK: {self.total_attack()}  DEF: {self.total_defense()}")
        print(f"XP: {self.xp}/{self.xp_to_next}  Gold: {self.gold}")
        weapon = self.equipped_weapon.name if self.equipped_weapon else "None"
        armor = self.equipped_armor.name if self.equipped_armor else "None"
        print(f"Weapon: {weapon} | Armor: {armor}")
        divider()

    def to_dict(self):
        return {
            "name": self.name,
            "char_class": self.char_class,
            "level": self.level,
            "xp": self.xp,
            "xp_to_next": self.xp_to_next,
            "gold": self.gold,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "attack": self.attack,
            "defense": self.defense,
            "crit_chance": self.crit_chance,
            "inventory": [i.to_dict() for i in self.inventory],
            "equipped_weapon": self.equipped_weapon.to_dict() if self.equipped_weapon else None,
            "equipped_armor": self.equipped_armor.to_dict() if self.equipped_armor else None,
        }

    @staticmethod
    def from_dict(d):
        p = Player(d["name"], d["char_class"])
        p.level = d["level"]
        p.xp = d["xp"]
        p.xp_to_next = d["xp_to_next"]
        p.gold = d["gold"]
        p.hp = d["hp"]
        p.max_hp = d["max_hp"]
        p.attack = d["attack"]
        p.defense = d["defense"]
        p.crit_chance = d["crit_chance"]
        p.inventory = [Item.from_dict(i) for i in d["inventory"]]
        p.equipped_weapon = Item.from_dict(d["equipped_weapon"]) if d["equipped_weapon"] else None
        p.equipped_armor = Item.from_dict(d["equipped_armor"]) if d["equipped_armor"] else None
        return p


class Enemy(Character):
    def __init__(self, name, hp, attack, defense, xp_reward, gold_reward, crit_chance=0.1):
        super().__init__(name, hp, attack, defense)
        self.xp_reward = xp_reward
        self.gold_reward = gold_reward
        self.crit_chance = crit_chance


ENEMY_TEMPLATES = [
    lambda: Enemy("Goblin", 35, 7, 2, 30, 15),
    lambda: Enemy("Giant Rat", 20, 5, 1, 15, 8),
    lambda: Enemy("Skeleton", 45, 10, 4, 40, 20),
    lambda: Enemy("Bandit", 55, 12, 5, 50, 35),
    lambda: Enemy("Orc Brute", 70, 15, 6, 65, 40),
    lambda: Enemy("Dark Cultist", 60, 18, 3, 70, 45),
]

BOSS = lambda: Enemy("The Dungeon Warden", 180, 22, 10, 300, 200, crit_chance=0.2)


# --------------------------------------------------------------------------
# COMBAT SYSTEM
# --------------------------------------------------------------------------

def combat(player, enemy):
    slow_print(f"\nA wild {enemy.name} appears! (HP: {enemy.hp})")
    while player.is_alive() and enemy.is_alive():
        divider()
        print(f"Your HP: {player.hp}/{player.max_hp}   {enemy.name} HP: {enemy.hp}")
        print("1. Attack  2. Use Potion  3. Flee")
        choice = input("> ").strip()

        if choice == "1":
            crit = random.random() < player.crit_chance
            dmg = player.total_attack() * (2 if crit else 1)
            dealt = enemy.take_damage(dmg)
            if crit:
                slow_print(f"CRITICAL HIT! You deal {dealt} damage to {enemy.name}!")
            else:
                slow_print(f"You deal {dealt} damage to {enemy.name}.")
        elif choice == "2":
            potions = [i for i in player.inventory if i.item_type == "potion"]
            if not potions:
                print("You have no potions!")
                continue
            for idx, p in enumerate(potions, 1):
                print(f"{idx}. {p}")
            try:
                sel = int(input("Choose a potion: ")) - 1
                player.use_potion(potions[sel])
            except (ValueError, IndexError):
                print("Invalid choice.")
                continue
        elif choice == "3":
            if random.random() < 0.5:
                slow_print("You successfully fled!")
                return "fled"
            else:
                slow_print("You failed to flee!")
        else:
            print("Invalid choice.")
            continue

        if not enemy.is_alive():
            break

        # Enemy turn
        dodge_chance = 0.05
        if random.random() < dodge_chance:
            slow_print(f"You dodge {enemy.name}'s attack!")
        else:
            crit = random.random() < enemy.crit_chance
            dmg = enemy.attack * (2 if crit else 1)
            dealt = player.take_damage(dmg)
            if crit:
                slow_print(f"{enemy.name} lands a CRITICAL HIT for {dealt} damage!")
            else:
                slow_print(f"{enemy.name} attacks you for {dealt} damage.")

    if not player.is_alive():
        return "dead"
    if not enemy.is_alive():
        slow_print(f"\nYou defeated {enemy.name}!")
        player.gain_xp(enemy.xp_reward)
        player.gold += enemy.gold_reward
        slow_print(f"You found {enemy.gold_reward} gold.")
        return "won"


# --------------------------------------------------------------------------
# SHOP
# --------------------------------------------------------------------------

def shop(player):
    while True:
        divider()
        print(f"WELCOME TO THE SHOP (Gold: {player.gold})")
        for idx, item in enumerate(SHOP_ITEMS, 1):
            print(f"{idx}. {item}")
        print("0. Leave shop")
        choice = input("Buy item number (or 0): ").strip()
        if choice == "0":
            break
        try:
            item = SHOP_ITEMS[int(choice) - 1]
        except (ValueError, IndexError):
            print("Invalid choice.")
            continue
        if player.gold < item.price:
            print("Not enough gold!")
            continue
        player.gold -= item.price
        new_item = Item(item.name, item.item_type, item.value, item.price)
        player.add_item(new_item)
        slow_print(f"You bought {item.name}!")


def manage_inventory(player):
    while True:
        divider()
        if not player.inventory:
            print("Your inventory is empty.")
            press_enter()
            return
        print("INVENTORY:")
        for idx, item in enumerate(player.inventory, 1):
            print(f"{idx}. {item}")
        print("0. Back")
        choice = input("Select item to use/equip (or 0): ").strip()
        if choice == "0":
            break
        try:
            item = player.inventory[int(choice) - 1]
        except (ValueError, IndexError):
            print("Invalid choice.")
            continue
        if item.item_type == "potion":
            player.use_potion(item)
        else:
            player.equip(item)


# --------------------------------------------------------------------------
# SAVE / LOAD
# --------------------------------------------------------------------------

def save_game(player, progress):
    data = {"player": player.to_dict(), "progress": progress}
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=2)
    slow_print("Game saved!")


def load_game():
    if not os.path.exists(SAVE_FILE):
        return None, 0
    with open(SAVE_FILE, "r") as f:
        data = json.load(f)
    player = Player.from_dict(data["player"])
    progress = data.get("progress", 0)
    return player, progress


# --------------------------------------------------------------------------
# MAIN GAME LOOP
# --------------------------------------------------------------------------

def create_character():
    print("Choose your class:")
    print("1. Warrior - High HP and defense")
    print("2. Mage    - High attack, low HP")
    print("3. Rogue   - High critical hit chance")
    class_map = {"1": "Warrior", "2": "Mage", "3": "Rogue"}
    while True:
        choice = input("> ").strip()
        if choice in class_map:
            break
        print("Invalid choice.")
    name = input("Enter your character's name: ").strip() or "Adventurer"
    player = Player(name, class_map[choice])
    slow_print(f"\nWelcome, {name} the {class_map[choice]}! Your journey begins...")
    return player


def explore(player, progress):
    divider()
    print(f"You are exploring the dungeon. (Room {progress + 1})")
    print("1. Venture deeper  2. Check status  3. Inventory  4. Rest at camp (heal, costs 10 gold)")
    print("5. Save game  6. Quit to menu")
    choice = input("> ").strip()

    if choice == "1":
        roll = random.random()
        if roll < 0.65:
            enemy = random.choice(ENEMY_TEMPLATES)()
            # scale enemy slightly with progress
            enemy.hp += progress * 5
            enemy.attack += progress
            result = combat(player, enemy)
            if result == "dead":
                return "dead", progress
            if result == "won":
                progress += 1
        elif roll < 0.85:
            gold_found = random.randint(10, 40)
            player.gold += gold_found
            slow_print(f"You find a small chest with {gold_found} gold!")
            progress += 1
        else:
            slow_print("The room is empty. You move on.")
            progress += 1

        if progress >= 8:
            slow_print("\nYou sense a powerful presence ahead... the Dungeon Warden awaits!")
            result = combat(player, BOSS())
            if result == "dead":
                return "dead", progress
            elif result == "won":
                return "victory", progress
            else:
                return "continue", progress

    elif choice == "2":
        player.status()
        press_enter()
    elif choice == "3":
        manage_inventory(player)
    elif choice == "4":
        if player.gold >= 10:
            player.gold -= 10
            player.hp = player.max_hp
            slow_print("You rest and recover to full HP.")
        else:
            print("Not enough gold to rest.")
        press_enter()
    elif choice == "5":
        save_game(player, progress)
        press_enter()
    elif choice == "6":
        return "menu", progress
    else:
        print("Invalid choice.")

    return "continue", progress


def main_menu():
    print("=" * 50)
    print("               DUNGEON QUEST")
    print("=" * 50)
    print("1. New Game")
    print("2. Load Game")
    print("3. Quit")
    return input("> ").strip()


def game_loop():
    while True:
        choice = main_menu()
        if choice == "1":
            player = create_character()
            progress = 0
        elif choice == "2":
            player, progress = load_game()
            if player is None:
                print("No saved game found.")
                continue
            slow_print(f"Welcome back, {player.name}!")
        elif choice == "3":
            print("Farewell, adventurer.")
            break
        else:
            print("Invalid choice.")
            continue

        # Optional: visit shop before diving in
        while True:
            print("\n1. Enter the dungeon  2. Visit the shop")
            pre = input("> ").strip()
            if pre == "2":
                shop(player)
            elif pre == "1":
                break

        state = "continue"
        while state == "continue":
            state, progress = explore(player, progress)

        if state == "dead":
            slow_print(f"\n{player.name} has fallen in the dungeon. GAME OVER.")
            if os.path.exists(SAVE_FILE):
                os.remove(SAVE_FILE)
        elif state == "victory":
            slow_print("\n*** YOU DEFEATED THE DUNGEON WARDEN! ***")
            slow_print("Congratulations, you have conquered Dungeon Quest!")
            if os.path.exists(SAVE_FILE):
                os.remove(SAVE_FILE)
        elif state == "menu":
            continue


if __name__ == "__main__":
    try:
        game_loop()
    except KeyboardInterrupt:
        print("\n\nGame interrupted. Farewell!")
