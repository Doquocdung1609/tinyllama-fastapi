"""Bound supplied object trees before serialization; never execute supplied text."""
from pydantic import BaseModel


def validate_budget(value):
    stack=[(value,0,frozenset())]; nodes=characters=0
    while stack:
        item,depth,ancestors=stack.pop(); nodes+=1
        if nodes>20000 or depth>20:
            raise ValueError('INPUT_COMPLEXITY_BUDGET')
        if isinstance(item,str):
            characters+=len(item)
            if characters>250000:
                raise ValueError('INPUT_CHARACTER_BUDGET')
        elif isinstance(item,(BaseModel,dict,list,tuple)):
            if id(item) in ancestors:
                raise ValueError('CYCLIC_INPUT')
            children=item.__dict__ if isinstance(item,BaseModel) else item
            if len(children)>5000:
                raise ValueError('INPUT_CONTAINER_BUDGET')
            ancestry=ancestors|{id(item)}
            if isinstance(children,dict):
                stack.extend((x,depth+1,ancestry) for pair in children.items() for x in pair)
            else:
                stack.extend((x,depth+1,ancestry) for x in children)
