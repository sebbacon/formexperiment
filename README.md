This is a quick proof of concept to play around with the forms system
I think I'd like to see.

I think most people I work with agree that we want our validation and
model updating to be lightweight.  This means that updating a model
should go something like:

    form <--> form.validate() --> form.to_json() --> model.from_json()
      ^
      |
    model.to_json()

This should all happen explicitly rather than magically.  There should
be no tight coupling between the model and its validation.  The
model's JSON input and outputs should be minimal and can therefore
easily support protocols other than HTTP.  Validation is pretty easily
handled by a number of lightweight libraries; my preference would be
the validators in formish (as in this example -- very lightweight) or
formencode.

Converting from form data (all strings) to properly typed JSON could
be handled by a lightweight schema framework, such as is also provided
by the above packages.  (Not implemented in this proof of concept)

The trickier question, which is what most of this hack plays around
with, is how to marshal flat form data to structured form data.  I
found Chris McDonough's [Peppercorn][1] approach intriguing, so most of
what's here is an attempt to work with that.

Peppercorn parses a stream of tokens into a structure.  I think it's a
nice idea.  

The approach to forms that I favour is allowing developers to write
their own forms.  After all, it's not actually that hard.  I don't
like all these frameworks that generate widgets for me; they're great
out the box, but the moment they need customising things get hairy
pretty quickly.

Many frameworks require magic form element names like
```name.status3.thing0``` which gets hard to track and read for
deeply-nested structures.  The nice thing about Peppercorn is that you
don't need to remember this stuff.

You still need to write lots of conditional code in your templates to
display errors and default data and so on.  Mostly, this package is
playing around with the idea that you might be able to write vanilla
HTML forms in a predefined structure, and then the framework fills
them out and adds the magic encoding for you.

For example, one of the tests uses a form that looks like this:

    <form action="">
     <input type="hidden" name="schema" value="myschema"/>
     <fieldset class="fieldset people">
      <div class="field">
       <label for="name">Name</label>
       <div class="error-message" />
       <input type="text" name="name" />
      </div>
      <div class="field">
       <label for="age">Age</label>
       <div class="error-message" />
       <input type="number" name="age" />
      </div>
     </fieldset>
    </form>

The convention is that anything that may be repeated (things that
would end up in a list when deserialized) are in a fieldset which has
a class attribute which would end up being the name of the list.

A field must be in an element with class ```field```.  Within that should
be a form element and an element of class ```error-message```, where any
error message would go.

There should be a hidden field that specifies the schema against which
the form will be validated / marshalled.

This approach works nicely for the simple cases, but I have a feeling
that it's going to fail for the more complex cases, where we need
access to loop variables to do conditional formatting, or similar.
(At the moment the contents of the "people" fieldset above are copied
for each loop iteration, but without any loop variables made available
to a templating language; the HTML is post-processed).

The balance I'm leaning towards at the moment would be to write the
forms in your favourite templating language, and add in peppercorn
tokens by hand.

I just noticed whitmo's [snippet][2] on Github which appears to use
peppercorn + htmlfill/formencode to do the same thing -- probably a
much better idea to reuse these than reproduce -- needs investigation.

Look at the tests to see how it works.  Start with the doctest
```test_simple_data.txt``` for a version without peppercorn, then move
onto ```test_with_peppercorn``` for more examples.  (One is disabled
as it's not working yet -- there's a bug with lists-within-lists).

[1]: http://www.plope.com/peppercorn
[2]: https://gist.github.com/396568
