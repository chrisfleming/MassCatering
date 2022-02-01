Mass Catering - menu compiler
=============================

The basic use of this is to take a bunch of recipes work out the quantities for the number of servings requested, and finally produce scaled up versions of each recipe as well as a complete shopping list.

Example usage:

```
./compile_menu.py [-h] [-o OUTPUT] [-p] [menu]

Compile a menu and calculate the required quantities.

positional arguments:
  menu                  YAML file describing menu.

optional arguments:
    -h, --help            show help message
    -o OUTPUT, --output OUTPUT
                          Output directory
    -v, --verbose     Verbose output, printing explicit menu parsing and
                            adding of items.
    -r ROUND, --round ROUND
                      Set rounding to specified number of decimal places (default=2).
    -p, --pdf-generation  Use pandoc to generate pdf from all markdown files in menu
    				  - requires pandoc and latex
```


Compile md to pdf requires pandoc and latex installations.

# Standards
Convention when creating a recipe, is that all ingredients are defined in the singular. 

If an item does not exist, add it to the unit_registry, with the average weight of that item, so that an item weight can be calculated instead of number of items.

Generic items can included, without adding to the unit registry, through the use of 'quantity', which is used as a dimensionless quantity, to allow for quick addition of items.
