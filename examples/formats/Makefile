# Example: `make` configuration file.
# See: https://www.gnu.org/software/make/manual/make.html
# NOTE: There are significant differences between how we parse this file
# and how `make` parses it. Every supported feature is listed in this file.
#
# Here are some things that are known to be unsupported:
# Not supported: (03.01.01) .POSIX
# Not supported: (03.03.00) include
# Not supported: (04.09.00) special built-in target names
# Not supported: (04.10.00) grouped targets
# Not supported: (04.11.00) multiple rules for one target
# Not supported: (04.13.00) double-colon rules
# Not supported: (06.00.00) variables
# Not supported: (07.00.00) conditionals
# Not supported: (08.00.00) functions
# Not supported: (10.00.00) implicit rules

# Supported: change prefix
.RECIPEPREFIX = > # sets to greater than symbol

# both of these reset back to tab
.RECIPEPREFIX
.RECIPEPREFIX=

# Ignored: (04.06.00) `.PHONY` target
# We treat all targets as .PHONY
.PHONY: basic1 basic2

# A basic command runs one or more shell commands.
basic1:
	echo 'Hello'
	echo 'World'

basic2: # put helpful descriptions here
	ls -la

# A composite command calls its prerequisites before it is executed.
composite1: basic1 basic2

# You can put a space before the colon.
composite2 : basic1
	echo 'Do this afterwards'

# We support line continuations both in the prerequisites and recipes.
composite3: basic1 \
						basic2
	echo "This is a very \
	long line."


# Argument Interpolation: pass arguments to tasks (use pdm-style)
# supply defaults
test1:
	pytest {args:src test}

# interpolate the first argument (required)
# and then interpolate the remaining arguments, if any
lint1:
	ruff check $1 {args:}

# you can call other tasks from the recepies and provide arguments
lint2:
	lint1 . --fix

# Environment Variables: pass environment variables to tasks
# Files are resolved relative to the configuration file.
# If the .env file has "FLASK_PORT=8080", the following are equivalent.
env1:
	FLASK_PORT=8080
	flask run --debug

env2:
	source .env
	flask run --debug

# Error Suppression: run tasks even when previous tasks fail
will_fail:
	exit 1 # will exit with error code 1

keep_going:
	-exit 1 # Makefile-style, note the dash symbol

# suppress within a composite
keep_going3: +will_fail
	echo Works

# Working Directory: where does a task run?
# Run in the directory one level up from the configuration file.
working:
	cd ..
	ls -la

# Supported: multiple targets
# https://www.gnu.org/software/make/manual/make.html#Multiple-Targets
big little: text.g
	generate $< -$@ > $@output

# Partially supported: automatic variables
# https://www.gnu.org/software/make/manual/make.html#Automatic-Variables
# - $@ name of the target
# - $< first prerequisite
# - $? all prerequisites (not supported: "newer than target")
# - $^ all prerequisites only once
