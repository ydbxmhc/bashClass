#!/usr/bin/bash

. boop Greeter

Greeter.greet

into=g Greeter name="from Boop"
into=msg $g.greet
printf "%s\n" "$msg"

into=b Greeter
_EOL=" It's nice to meet you!"$'\n' $b.greet

# inline subclass
FancyGreeter.greet() { # overwrite inherited method
  local _Self="${_Self:-}" _Class="${_Class:-FancyGreeter}" __FancyGreeter_greet_tmp
  into=__FancyGreeter_greet_tmp _Super greet                                  # call parent class's method
  boop.pass "✨ ${__FancyGreeter_greet_tmp// Class/ +Sublass+} ✨" ${into:-}  # append a fancy sparkle
}
boopClass FancyGreeter isa:Greeter has:name public:greet

FancyGreeter.greet
into=g FancyGreeter name="from *Fancy*"
into=msg $g.greet
printf "%s\n" "$msg"
into=b FancyGreeter
_EOL=" It's NICER to meet you!"$'\n' $b.greet

