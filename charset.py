class HashByValue:
	def value(self):
		pass
	def _value(self):
		return (self.__class__, self.value())
	def __eq__(self, other):
		return self._value() == other._value()
	def __hash__(self):
		return hash(self._value())


class CharSet(HashByValue):
	min_char = 0
	max_char = 127
	def __init__(self, *ranges, inverted=False):
		ranges = sorted((_, _) if isinstance(_, int) else _ for _ in ranges)
		self.ranges = []
		last = CharSet.min_char-1
		for min_char, max_char in ranges:
			if min_char <= last:
				min_char, old_max_char = self.ranges.pop()
				max_char = max(max_char, old_max_char)
			self.ranges.append((min_char, max_char))
			last = max_char+1

		if inverted:
			self.ranges = self.star.intersect(self)[0].ranges

	def value(self):
		return tuple(self.ranges)

	def contains(self, char):
		return any(min_char <= char <= max_char for min_char, max_char in self.ranges)

	def union(self, other):
		return CharSet(*self.ranges, *other.ranges)

	def intersect(self, other):
		in_self = []
		in_both = []
		in_other = []
		i = 0
		j = 0
		get = lambda l, i: l[i] if i < len(l) else (CharSet.max_char+1, CharSet.max_char+1)
		self_min, self_max = get(self.ranges, i)
		other_min, other_max = get(other.ranges, j)
		while i < len(self.ranges) or j < len(other.ranges):
			if self_max < other_min:
				i += 1
				in_self.append((self_min, self_max))
				self_min, self_max = get(self.ranges, i)
				continue
			if other_max < self_min:
				j += 1
				in_other.append((other_min, other_max))
				other_min, other_max = get(other.ranges, j)
				continue

			if self_min < other_min:
				in_self.append((self_min, other_min-1))
				self_min = other_min
			if other_min < self_min:
				in_other.append((other_min, self_min-1))
				other_min = self_min

			if self_max < other_max:
				i += 1
				in_both.append((self_min, self_max))
				other_min = self_max+1
				self_min, self_max = get(self.ranges, i)
			elif other_max < self_max:
				j += 1
				in_both.append((other_min, other_max))
				self_min = other_max+1
				other_min, other_max = get(other.ranges, j)
			else:
				i += 1
				j += 1
				in_both.append((self_min, self_max))
				self_min, self_max = get(self.ranges, i)
				other_min, other_max = get(other.ranges, j)
		return CharSet(*in_self), CharSet(*in_other), CharSet(*in_both)

	def is_empty(self):
		return len(self.ranges) == 0

	def get_one(self):
		if self.is_empty():
			return ""
		return chr(self.ranges[0][0])

	def __repr__(self):
		if self.is_empty():
			return "ε"
		if self == CharSet.star:
			return "."
		if len(self.ranges) == 1 and self.ranges[0][0] == self.ranges[0][1]:
			return f"{chr(self.ranges[0][0])}"
		return "["+"".join(f"{chr(min_char)}" if min_char==max_char else f"{chr(min_char)}-{chr(max_char)}" for min_char, max_char in self.ranges)+"]"

CharSet.star = CharSet((CharSet.min_char, CharSet.max_char))


class TransitionTable:
	def __init__(self):
		self.entries = {}

	def insert_state(self, path, state):
		transitions = self.entries
		for other_path, other_state in list(transitions.items()):
			if state == other_state:
				del transitions[other_path]
				cover = path.union(other_path)
				transitions[cover] = state
				break
		else:
			transitions[path] = state
		
	def insert(self, path, value):
		transitions = self.entries
		for other_path, other_state in list(transitions.items()):
			path, in_other, in_both = path.intersect(other_path)
			if in_both.is_empty():
				continue
			del transitions[other_path]
			if value not in other_state:
				both_state = set(other_state)
				both_state.add(value)
				if not in_other.is_empty():
					transitions[in_other] = other_state
				self.insert_state(in_both, both_state)
			else:
				cover = in_both.union(in_other)
				transitions[cover] = other_state
			if path.is_empty():
				break
		else:
			state = set((value,))
			self.insert_state(path, state)


def to_string(entry):
	return "".join(_.get_one() if isinstance(_, CharSet) else chr(_) for _ in entry)


def to_ascii(entry):
	return list(map(ord, entry))
