#!/usr/bin/env python3

import yaml
import re
import sys
import os
from pint import UnitRegistry
from argparse import ArgumentParser

ureg = UnitRegistry()
ureg.load_definitions('unit_registry.txt')
# 1 tsp smoked paprika = 3.3g

def get_args():
    """
    Read the arguments and return them to main.
    """
    parser = ArgumentParser(description="Compile a menu and calculate "
                            "the required quantities.")
    parser.add_argument('menu', nargs='?',
                        help="YAML file describing menu.")
    parser.add_argument('-o', '--output', default="output",
                        help="Output directory")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='verbose output, printing explicit menu parsing and adding of items.')
    parser.add_argument('-p', '--pdf-generation', action='store_true',
                        help="Use pandoc to generate pdf from all markdown files in menu - requires pandoc and latex")
    return parser.parse_args()

def open_yaml(file):
    with open(file, 'r') as stream:
        try:
            data = yaml.load(stream, Loader=yaml.SafeLoader)
        except yaml.YAMLError as exc:
            print(exc)
    return data


def amount_units(string):
    """
    Extract amount and unit from string and return a tuple of strings.
    >>> amount_units("0.4")
    ('0.4', '')
    >>> amount_units(".3 g")
    ('.3', 'g')
    >>> amount_units("50ml")
    ('50', 'ml')
    >>> amount_units("3.3 g")
    ('3.3', 'g')
    """
    regex = r"(?P<number>\d+(\.\d+)?|(\.\d+)?)\s*(?P<unit>[a-zA-Z_]*)"
    matches = re.match(regex, str(string))
    gd = matches.groupdict()
    return (gd['number'], gd['unit'])


class Ingredient():
    """A Class to store ingredients - hopefully also do unit conversions 
    if needed"""
    

    def __init__(self, name, quantity):
        self.name = name
        self.quantity = quantity

    def add(self, quantity):
        self.quantity = self.quantity + quantity

    def pr(self):
        return '{!s}'.format(self.value)

class Ingredients():
    """ All the ingredients """

    food = open_yaml("food.yaml")
    default_shop = "Supermarket"
    shops = dict()

    # Unit equivalents.
    equi = dict()
    equi['garlic_cloves'] = ['garlic']


    def __init__(self):
        self.list = dict()

    def add(self, ingredient, quantity):
        ingredient = self.equivalent_check(ingredient)
        if ingredient in self.list:
            a = self.list[ingredient]
            verboseprint('Adding', quantity, ingredient)
            a.add(quantity)
            self.list[ingredient] = a
        else: # add ingredient to list
            if ingredient in self.food and 'unit' in self.food[ingredient]:
                quantity = ureg('0 '+self.food[ingredient]['unit']) + quantity
            verboseprint('Adding', quantity, ingredient)
            self.list[ingredient] = Ingredient(ingredient, quantity)

    def equivalent_check(self, ingredient):
        for equivalent in self.equi:
            if ingredient in self.equi[equivalent]:
                return equivalent

        return ingredient

    def all_byshop(self):
        output = "# Shopping List\n\n"
        for item_ in sorted(self.list):
            item = self.list[item_]
            try:
              this_shop = self.food[item.name]['shop']
            except KeyError:
                this_shop = self.default_shop

            if this_shop in self.shops:
                self.shops[this_shop] = self.shops[this_shop] + "    [ ] {:~P} {!s}\n".format(item.quantity, item.name)
            else:
                self.shops[this_shop] = "    [ ] {:~P} {!s}\n".format(item.quantity, item.name)

        for shop in self.shops:
            output +=  "## %s\n" % (shop)
            output += self.shops[shop] + "\n"

        return output


def set_verbose_print(vprint):
    global verboseprint
    if vprint:
        def verboseprint(*args):
        # Print each argument separately so caller doesn't need to
        # stuff everything to be printed into a single string
            for arg in args:
                print(arg,end=' ')
            print()
    else:   
        verboseprint = lambda *a: None      # do-nothing function

def process_menu(menu_yaml, outdir, pdf_generation):
    ingredients = Ingredients()
    menu = open_yaml(menu_yaml)
    os.makedirs(outdir, exist_ok = True)

    for recipe_name in menu:
        skip = False
        try:
            file = "recipe/" + recipe_name + ".yaml"
            recipe = open_yaml(file)
        except FileNotFoundError:
            # not very elegant
            verboseprint("Can't open %s as recipe... trying as single ingredient" % recipe_name)
            if isinstance(menu[recipe_name], (int, float)):
                try:
                    amount = ureg(str(menu[recipe_name])+recipe_name)
                except:
                    amount = ureg(str(menu[recipe_name])+'quantity')
            else:
                amount = ureg(menu[recipe_name])

            verboseprint(recipe_name, ':', amount)
            ingredients.add(recipe_name, amount)
            skip = True
            continue

        if not skip:
            for day in menu[recipe_name]:
                people = int(menu[recipe_name][day])
                mdname = os.path.basename(recipe_name + ".md")
                if day != 'people':
                    mdname = day + '_' + mdname
                    verboseprint(mdname)

                f = open(os.path.join(outdir, mdname), "w")
                f.write("# {!s} {!s}\n".format(day, recipe['name']))
                f.write("\n")

                # DO we have serves?
                if 'serves' in recipe:
                    serves = float(recipe['serves'])
                    f.write("### Serves: {!s}\n".format(people))
                    f.write("\n")
                else:
                    serves = float(1)

                f.write("### Ingredients: \n")
                f.write("\n")
                for ingredient in recipe['ingredients']:
                    # There must be a better way of testing whether or not an item has been defined
                    if isinstance(recipe['ingredients'][ingredient], (int, float)):
                        try:
                            verboseprint('trying to use predefined item', ingredient)
                            amount = ureg(str(recipe['ingredients'][ingredient])+ingredient)
                        except: 
                            verboseprint('failed - defining new item',  ingredient, '- set to dimensionless quantity')
                            # Currently set undefined items to a 'quantity' rather than the individual defined item
                            amount = ureg(str(recipe['ingredients'][ingredient])+'quantity')
                    else:
                        amount = ureg(recipe['ingredients'][ingredient])

                    amount_pp = amount/serves
                    f.write('\t{!s}: {!s}\n'.format(ingredient, amount_pp * people))
                    ingredients.add(ingredient, amount_pp * people)

                if 'method' in recipe:
                    try:
                        f.write("\n\n### Description\n")
                        f.write(recipe['method'])#.encode('utf-8'))
                        f.write("\n")
                    except:
                        pass
                if pdf_generation:
                    f.write("\n\pagebreak")
                f.close()

    outfile = open(os.path.join(outdir, "shoppinglist.md"), "w")
    outfile.write(ingredients.all_byshop())
    if pdf_generation:
        outfile.write('\pagebreak')
    outfile.close()

    if pdf_generation:
        pandoc_input = os.path.join(outdir, "*.md")
        pandoc_output = os.path.join(outdir, "All_Recipe.pdf")
        os.system("pandoc {!s} --pdf-engine=xelatex -o {!s}".format(pandoc_input,pandoc_output))


if __name__ == "__main__":
    args = get_args()
    set_verbose_print(args.verbose)
    process_menu(args.menu, args.output, args.pdf_generation)
