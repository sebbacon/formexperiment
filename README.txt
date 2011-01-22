This is a very quick proof of concept to try out the forms system I
think I'd like to see.

The salient point is that it makes no attempt to help you build a
form.  I always end up fighting form widget frameworks for edge cases,
and it's not that much effort coding the HTML by hand anyway.  So it
transforms a template with validated data, instead of generating the
HTML from the data.

It also, in theory, makes it easier to build model updating
functionality based around REST/JSON APIs and apply a form view later
with a minimum of effort.
