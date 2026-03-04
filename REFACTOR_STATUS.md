# Bash OOP Framework Refactoring Status

## Current Status: Design Phase - Not Yet Implemented

This document tracks the refactoring work to improve security, efficiency, and OOP correctness in the bash class system.

## Completed Design Work

### 1. Security Analysis
Identified critical security issues in current implementation:
- Command injection via `eval` with user-controlled input
- World-writable filesystem storage (`umask 0000`)
- No input validation on attribute values
- Global namespace pollution
- Predictable filesystem paths for object data

### 2. New Dispatcher Architecture (Designed, Not Implemented)

#### Core Components

**Validation Function** - Lean, fail-fast identifier validation:
```bash
__bashClass.validate() {
  [[ "$1" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || __bashClass.crash "Invalid identifier: '$1'"
}
```

**Method Registry** - Eliminates most `eval` usage:
```bash
declare -gA __bashClass_methodRegistry

__bashClass.registerMethod() {
  local class="$1" method="$2" impl="$3"
  __bashClass.validate "$class"
  __bashClass.validate "$method"
  __bashClass.validate "$impl"
  declare -f "$impl" >/dev/null || __bashClass.crash "Function '$impl' does not exist"
  __bashClass_methodRegistry["$class.$method"]="$impl"
}
```

**Unified Dispatcher** - Single function handles both class and object methods:
```bash
__bashClass.dispatch() {
  local self="${self:-${class:-bashClass}}" class="${class:-bashClass}"
  local method="$1"
  shift
  
  __bashClass.validate "$self"
  __bashClass.validate "$class"
  __bashClass.validate "$method"
  
  local key="$class.$method"
  local impl="${__bashClass_methodRegistry[$key]}"
  
  [[ -n "$impl" ]] || __bashClass.crash "Method not found: $key"
  
  self="$self" class="$class" "$impl" "$@"
}
```

#### Usage Pattern
```bash
# Define implementation
__Box_volume() {
  local -I self class
  printf "Volume calculation for %s\n" "$self"
}

# Register method
__bashClass.registerMethod Box volume __Box_volume

# Call as class method
class=Box __bashClass.dispatch volume

# Call as object method
self="_a1b2c3d4" class=Box __bashClass.dispatch volume
```

### 3. Design Principles Established

- **No sanitization, only validation** - Reject invalid input, don't try to clean it
- **Fail fast** - Crash immediately on invalid input
- **Avoid subshells** - Use validation instead of sanitization to eliminate subshell calls
- **Explicit over implicit** - Keep `self="$self" class="$class"` prefixes for clarity
- **Use printf, not echo** - More reliable output
- **Lean functions** - One-liners when possible for ADHD-friendly code density
- **Convention over enforcement** - Accept bash's global function limitation, use naming conventions

### 4. Naming Conventions

- **Generated/internal functions**: `__ClassName_methodName` (two underscores, underscore separator)
- **Registry keys**: `ClassName.methodName` (dots for OOP feel)
- **Only bash identifiers validated**: No dots in actual function names

## Outstanding Issues (Not Yet Addressed)

### Encapsulation
- All functions remain global (bash limitation)
- Filesystem-based storage is world-readable
- No private/protected/public distinction

### Inheritance
- No proper method resolution order
- No super() mechanism
- Manual attribute inheritance in subclasses

### Polymorphism
- Partial support via dispatcher (can call different implementations)
- No type checking or contracts
- Can't treat Cube as Box in type-safe way

### Efficiency
- Filesystem I/O for every attribute access (major bottleneck)
- Subshell spawning for attribute reads: `$($self.attribute)`
- No caching mechanism

## Latest Design Decisions (Session 2)

### Single Registry with Descriptor Values

Instead of complex keys, use simple identifiers with delimited descriptor strings:

```bash
declare -gA __bashClass_registry

# Key: simple identifier
# Value: delimited descriptor with all metadata
__bashClass_registry["Box"]="type=class|id=Box|parent=bashObject|methods=volume,area,top|properties=length,width,height|self=|impl="
__bashClass_registry["_a1b2c3d4"]="type=object|id=_a1b2c3d4|parent=|methods=|properties=|self=_a1b2c3d4|class=Box|length=5|width=3|height=7"
```

**Benefits:**
- Simple keys for O(1) lookup
- Self-documenting descriptors
- Easy serialization (save/restore entire registry)
- Consistent structure across all types
- Enables object cloning and IPC

### Method Resolution Order (MRO)

Dynamic search with caching for inherited methods:

```bash
__bashClass.dispatch() {
  # Check cache first
  local cache_key="$class.$method"
  local impl="${__bashClass_methodRegistry[$cache_key]}"
  
  # Cache miss? Walk inheritance chain
  if [[ -z "$impl" ]]; then
    local current_class="$class"
    while [[ -n "$current_class" ]]; do
      impl="${__bashClass_methodRegistry[$current_class.$method]}"
      [[ -n "$impl" ]] && break
      # Get parent without subshell
      __bashClass.parse "$current_class" "parent" current_class
    done
    # Cache for next time
    [[ -n "$impl" ]] && __bashClass_methodRegistry[$cache_key]="$impl"
  fi
}
```

**Decision:** Single inheritance only (for now). Multiple inheritance adds complexity without clear need.

### Subshell-Free Parsing with Namerefs

Use global counter to generate unique nameref names and avoid collisions:

```bash
declare -gi __bashClass_refCounter=0

__bashClass.parse() {
  local key="$1" field="$2"
  local -n __ref_$((++__bashClass_refCounter))="$3"
  local descriptor="${__bashClass_registry[$key]}"
  
  local pattern="\|${field}=([^|]*)"
  [[ "$descriptor" =~ $pattern ]] && __ref_$__bashClass_refCounter="${BASH_REMATCH[1]}"
}

# Usage - no subshell!
__bashClass.parse "Box" "parent" current_class
```

**Why counter over RANDOM/EPOCHREALTIME:** Guaranteed unique, no collision risk, no subshells.

### Serialization Support

Built-in save/restore for entire object graph:

```bash
__bashClass.serialize() {
  local file="${1:-objects.dat}"
  for key in "${!__bashClass_registry[@]}"; do
    printf "%s\t%s\n" "$key" "${__bashClass_registry[$key]}"
  done > "$file"
}

__bashClass.deserialize() {
  local file="${1:-objects.dat}"
  local key descriptor
  while IFS=$'\t' read -r key descriptor; do
    __bashClass.validate "$key"
    __bashClass_registry[$key]="$descriptor"
  done < "$file"
}
```

Enables: persistence, IPC, snapshots, debugging, testing, object cloning.

## Design Philosophy

### Inheritance vs Composition

**Support traditional inheritance** (single inheritance with MRO) for familiarity, but **prefer and recommend composition** for flexibility and simplicity. Composition avoids deep inheritance hierarchies and makes relationships explicit.

Example composition pattern:
```bash
# Instead of: Cube extends Box
# Prefer: Cube has-a Box (composition)
Cube.volume() {
  local box_calculator="$(__bashClass.getProperty "$self" "calculator")"
  $box_calculator.calculate "$size" "$size" "$size"
}
```

### User Interface / Syntax Design

**Critical consideration:** The visible usage syntax must be intuitive for both OOP developers AND bash users. Avoid "steampunk Lovecraftian nightmare" syntax.

**Goals:**
- Familiar to OOP users: `$object.method args` feels natural
- Familiar to bash users: Still looks like bash, not Java-in-disguise
- Readable: Clear what's happening without deep framework knowledge
- Minimal magic: Avoid too much hidden behavior

**Examples to evaluate:**
```bash
# Object creation - which feels better?
new Box length=5 width=3 height=7
Box.new length=5 width=3 height=7
mybox=$(Box.create length=5 width=3 height=7)

# Method calls - which is clearer?
$mybox.volume
$mybox volume
call $mybox volume
mybox.volume  # without $?

# Property access
$mybox.length
$mybox length
get $mybox length
```

**TODO:** Design and document the final syntax before implementation. Test with both OOP and bash-native users for feedback.

## Next Steps

1. **Design final user-facing syntax** (critical - do this first!)
2. Implement descriptor-based registry system
3. Build parser with nameref counter pattern
4. Implement MRO with caching in dispatcher
5. Add serialization/deserialization functions
6. Migrate Box/Cube to new system
7. Add benchmarking to measure improvements
8. Document composition patterns as preferred approach

## Notes

- This is a personal project for learning and showcasing quirky bash skills
- Security improvements prioritized over backward compatibility
- Efficiency is important but secondary to security
- Current code remains functional during refactoring
