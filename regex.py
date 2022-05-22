NOP = 0
END = 1
NEX = 2
DEFAULT_COPY = False

def extend(seq, *items):
	for item in items:
		if item not in seq:
			seq.add(item)

class Regex:
	def value(self):
		pass
	def __eq__(self, other):
		return self.value() == other.value()
	def __hash__(self):
		return hash(self.value())


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
			return self.expr+"_"
		return self.expr


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
		return "["+"".join(f"<{expr}>" if i==self.cursor else f"{expr}" for i, expr in enumerate(self.exprs))+"]"


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
				"""if copy.dirty:
					result.append((char, copy, NOP))
				elif self.count < self.min:
					result.append((char, copy, NOP))
				else:
					result.append((char, copy, END))
					if self.max is None or self.count < self.max:
						result.append((char, copy, NOP))"""
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
		return f"({self.expr}){{{self.min},{self.count},{self.max}}}"


class State(Regex):
	current_id = 0
	def new_id():
		State.current_id +=1
		return State.current_id
	def __init__(self, exprs, transitions=None):
		self.id = State.new_id()
		self.exprs = set(exprs)
		self.transitions = transitions or {}
		self.valid = False
	def value(self):
		return tuple(self.exprs)
	def __repr__(self):
		#return f"\nState {self.id}: {self.valid}"+"".join(f"\n - {expr.value()}" for expr in self.exprs)
		return f"\nState {self.id}: {self.valid}"+"".join(f"\n - {expr}" for expr in self.exprs)+"".join(f"\n > {char}->{state.id}" for char, state in self.transitions.items())


def equivalent(item, seq):
	for other in seq:
		if other == item:
			return other
	raise ValueError


def follow(expr, verbosity=0):
	first = State([expr])
	remaining_states = [first]
	states = set(remaining_states)
	while remaining_states:
		queue_states = set()
		for state in remaining_states:
			transitions = {}
			for expr in state.exprs:
				if verbosity>0: print(">", expr)
				for char, sub_expr, flag in expr.advance():
					if verbosity>0: print(char, sub_expr, flag)
					if char in transitions and sub_expr in transitions[char].exprs:
						if verbosity>0: print("already visited")
						if verbosity>1: input()
						continue
					if verbosity>1: input()
					if flag & NEX:
						state.valid = True
						continue
					if char in transitions:
						transitions[char].exprs.add(sub_expr)
					else:
						transitions[char] = State([sub_expr])
			if verbosity>1: print("transitions:", transitions)
			for char, sub_state in transitions.items():
				if sub_state in states:
					transitions[char] = equivalent(sub_state, states)
				else:
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


#e = Sequence(Atom("a"), Atom("b"), Atom("c"))
#e = Repeat(Atom("r"), 2, 3)
#e = Sequence(Atom("a"), Epsilon, Atom("b"), Epsilon, Epsilon, Epsilon)

n=30
a = Atom("a")
b = Atom("b")
c = Atom("c")
#e = a
#e = Epsilon
#e = Repeat(a,0,3)
#e = Repeat(a,3,4)
#e = Choice(a,b)
#e = Sequence(a,a,b)
#e = Repeat(Choice(a,b))
#e = Repeat(Sequence(a,Repeat(b,0,0)),0)
#e = Repeat(Sequence(a,Repeat(b,1)),0)
#e = Sequence(Repeat(Sequence(a,b),1),a,b)
#e = Sequence(b,Repeat(Repeat(a,0,1),2,2),b)
#e = Sequence(b,Repeat(a,0,2),b)
#e = Sequence(*[Repeat(a,0,1)]*n, *[a]*n)
e = Sequence(Repeat(Choice(a,b,c),0),a,b)
print(e)
states = follow(e)
for state in sorted(states, key=lambda s: s.id):
	print(state)
