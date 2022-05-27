from charset import HashByValue, CharSet, TransitionTable


NOP = 0
END = 1
NEX = 2
DEFAULT_COPY = False


class Regex(HashByValue):
	pass

class Atom(Regex):
	def __init__(self, char, cursor=False):
		self.expr = char
		self.cursor = cursor
	def value(self):
		return (self.expr, self.cursor)
	def advance(self):
		copy = self.copy()
		if self.cursor:
			return [(self.expr, copy, NEX)]
		copy.cursor = True
		return [(self.expr, copy, END)]
	def copy(self, deep=DEFAULT_COPY):
		return Atom(self.expr, self.cursor)
	def reset(self):
		self.cursor = False
	def __repr__(self):
		if self.cursor:
			return f"{self.expr}_"
		return f"{self.expr}"


class Epsilon(Regex):
	def __init__(self):
		pass
	def advance(self):
		return [(self, self, END|NEX)]
	def copy(self, deep=DEFAULT_COPY):
		return self
	def reset(self):
		pass
	def __repr__(self):
		return "ε"
Epsilon = Epsilon()


class Sequence(Regex):
	def __init__(self, *exprs, cursor=0):
		self.exprs = list(exprs)
		self.cursor = cursor
		self.n = len(exprs)
	def value(self):
		return (*self.exprs, self.cursor)
	def advance(self):
		if self.cursor >= self.n:
			return [(Epsilon, self.copy(), END|NEX)]
		result = []
		expr = self.exprs[self.cursor]
		for char, sub_expr, flag in expr.advance():
			copy = self.copy()
			copy.exprs[self.cursor] = sub_expr
			if flag & END:
				copy.cursor += 1
			if flag & NEX:
				result.extend(copy.advance())
			else:
				result.append((char, copy, self.cursor >= self.n))
		return result
	def copy(self, deep=DEFAULT_COPY):
		if deep:
			return Sequence(*(expr.copy(deep) for expr in self.exprs), cursor=self.cursor)
		return Sequence(*self.exprs, cursor=self.cursor)
	def reset(self):
		for expr in self.exprs:
			expr.reset()
		self.cursor = 0
	def __repr__(self):
		return "("+"".join(f"<{expr}>" if i==self.cursor else f"{expr}" for i, expr in enumerate(self.exprs))+")"


class Choice(Regex):
	def __init__(self, *exprs, cursor=None):
		self.exprs = list(exprs)
		self.cursor = cursor
	def value(self):
		return (*self.exprs, self.cursor)
	def advance(self):
		result = []
		if self.cursor is None:
			for i, expr in enumerate(self.exprs):
				copy = self.copy()
				copy.cursor = i
				result.extend(copy.advance())
			return result
		expr = self.exprs[self.cursor]
		for char, sub_expr, flag in expr.advance():
			copy = self.copy()
			copy.exprs[self.cursor] = sub_expr
			result.append((char, copy, flag))
		return result
	def copy(self, deep=DEFAULT_COPY):
		if deep:
			return Choice(*(expr.copy(deep) for expr in self.exprs), cursor=self.cursor)
		return Choice(*self.exprs, cursor=self.cursor)
	def reset(self):
		for expr in self.exprs:
			expr.reset()
		self.cursor = None
	def __repr__(self):
		return "("+"|".join(f"<{expr}>" if i==self.cursor else f"{expr}" for i, expr in enumerate(self.exprs))+")"


class Repeat(Regex):
	def __init__(self, expr, min=0, max=None, count=0, dirty=False):
		self.expr = expr
		self.min = min
		self.max = max
		self.count = count
		self.dirty = dirty
	def value(self):
		count = self.count
		if ((self.max is not None and count >= self.max) or
			(self.max is None and count >= self.min)):
			count = None
		return (self.expr, self.min, self.max, count)
	def advance(self):
		result = []
		if not self.dirty:
			if self.count >= self.min:
				copy = self.copy()
				copy.count = copy.min
				result.append((Epsilon, copy, END|NEX))
			if self.max is not None and self.count >= self.max:
				return result
		for char, sub_expr, flag in self.expr.advance():
			copy = self.copy()
			copy.dirty = True
			if flag & END:
				copy.count += 1
				copy.dirty = False
				sub_expr = sub_expr.copy(True)
				sub_expr.reset()
			copy.expr = sub_expr
			if flag & NEX:
				result.extend(copy.advance())
			else:
				result.append((char, copy, NOP))
		return result
	def copy(self, deep=DEFAULT_COPY):
		if deep:
			return Repeat(self.expr.copy(deep), self.min, self.max, self.count, self.dirty)
		return Repeat(self.expr, self.min, self.max, self.count, self.dirty)
	def reset(self):
		self.expr.reset()
		self.count = 0
		self.dirty = False
	def __repr__(self):
		return f"{self.expr}{{{self.min},{self.count},{self.max}}}"


class Family(Regex):
	def __init__(self, expr, id):
		self.expr = expr
		self.id = id
	def value(self):
		return (self.expr, self.id)
	def advance(self):
		result = []
		for char, sub_expr, flag in self.expr.advance():
			copy = self.copy()
			copy.expr = sub_expr
			result.append((char, copy, flag))
		return result
	def copy(self):
		return Family(self.expr, self.id)
	def reset(self):
		self.expr.reset()
	def __repr__(self):
		return f"#{self.id} {self.expr}"


class State(Regex):
	current_id = 0
	def new_id():
		State.current_id +=1
		return State.current_id
	def __init__(self, exprs, transitions=None):
		self.id = State.new_id()
		self.exprs = set(exprs)
		self.transitions = transitions or {}
		self.accept = set()
		self.valid = False
	def value(self):
		return tuple(self.exprs)
	def __repr__(self):
		return (f"\nState {self.id}: {self.valid}"
			+"".join(f"\n - {expr}" for expr in self.exprs)
			+"".join(f"\n + {expr}" for expr in self.accept)
			+"".join(f"\n {char} -> {state.id}" for char, state in self.transitions.items()))


def equivalent(item, seq):
	for other in seq:
		if other == item:
			return other
	raise ValueError


def follow(*exprs, verbosity=0):
	first = State([Family(expr, i) for i, expr in enumerate(exprs)])
	#first = State(list(exprs))
	print(first)
	print("=================================")
	remaining_states = [first]
	states = set(remaining_states)
	while remaining_states:
		queue_states = set()
		for state in remaining_states:
			transitions = TransitionTable()
			for expr in state.exprs:
				if verbosity>0: print(">", expr)
				for char, sub_expr, flag in expr.advance():
					if verbosity>0: print(char, sub_expr, flag)
					if verbosity>1: input()
					if flag & NEX:
						state.valid = True
						state.accept.add(expr)
						continue
					transitions.insert(char, sub_expr)
			if verbosity>1: print("transitions:", transitions)
			entries = transitions.entries.items()
			transitions = {}
			for char, exprs in entries:
				sub_state = State(exprs)
				if sub_state in states:
					transitions[char] = equivalent(sub_state, states)
				else:
					transitions[char] = sub_state
					states.add(sub_state)
					queue_states.add(sub_state)
			state.transitions = transitions
		remaining_states = queue_states
		if verbosity>2:
			print("\nQUEUED STATES:", queue_states)
			print("\nSTATES:")
			for state in sorted(states, key=lambda s: s.id):
				print(state)
	return states
