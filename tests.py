from regex import *


n=2
a = Atom(CharSet(97))
b = Atom(CharSet(98))
c = Atom(CharSet(99))
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
states = follow(e, b)
for state in sorted(states, key=lambda s: s.id):
	print(state)
