from copy import deepcopy
from lxml import etree
import types

import schemaish
import peppercorn
from peppercorn import START
from peppercorn import END
from peppercorn import SEQUENCE
from peppercorn import MAPPING

schema_registry = {}

TEMPLATE_CLASS = "transformer-template"


def get_validated(data):
    # the schema should be specified in the data.  It may be passed in
    # as a form variable (viz. data['data']['schema']) or explicitly
    # as data['schema'].  We normalize it:
    try:
        schema_name = data['data'].pop('schema')
        data['schema'] = schema_name
    except KeyError:
        pass
    if isinstance(data['schema'], schemaish.Structure):
        schema = data['schema']
    else:
        schema = schema_registry.get(data['schema'])
    # now we have the schema, validate it and store any errors in the
    # data dict
    try:
        schema.validate(data['data'])
    except schemaish.Invalid, e:
        errors = {}
        for k, v in e.error_dict.items():
            errors[k] = v.message
        data['errors'] = errors
    return data


class ParsedElement(object):
    def __init__(self, element):
        self.element = element

    def __repr__(self):
        return "%s" % etree.tostring(self.element)

    def append(self, item):
        if isinstance(item, ParsedElement):
            self.element.append(item.element)
        else:
            self.element.append(item)

    def xpath(self, query):
        return self.element.xpath(query)

    def delete(self):
        self.element.getparent().remove(self.element)

    def get_fields(self, name=None):
        """Return all fields matching 'name'
        """
        selectors = ['//input',
                     '//textarea',
                     ]
        if name:
            selectors = [x + '[@name="%s"]' % name for x in selectors]
        xpaths = "|".join(selectors)
        return self.element.xpath(xpaths)

    def get_field(self, name=None):
        """Return a contained ParsedFormField, optionally selected by
        name attribute. If there are several, and they're all in the
        same fieldset, return the a field with the class
        TEMPLATE_CLASS.
        """
        match = self.get_fields(name)
        if match:
            if len(match) > 1:
                # this is OK as long as one is a template and they're
                # all in the same fieldset
                template_matched = []
                fieldsets = set()
                for m in match:
                    m = ParsedFormField(m)
                    container = m.get_outer_container()
                    fieldsets.add(m.get_outer_fieldset())
                    if container.is_template():
                        template_matched.append(m.element)
                if len(template_matched) == 1:
                    match = template_matched
                else:
                    if len(template_matched) > 1:
                        msg = "More than one template element '%s'"
                    elif len(fieldsets) > 1:
                        msg = "'%s' present in more than one fieldset"
                    else:
                        msg = "More than one form element '%s'"
                    raise Exception(msg % name)
        else:
            raise Exception(
                "Could not find element '%s'" % name)
        return ParsedFormField(match[0])

    def is_template(self):
        if TEMPLATE_CLASS in self.element.attrib['class']:
            return True

    def get_fieldset(self, name):
        """Return a ParsedFieldSet, selected by class attribute
        """
        match = self.form.xpath(
            "//fieldset[contains(@class, '%s')]" % name)
        return ParsedFieldSet(match[0])

    def get_outer_fieldset(self):
        fieldset = self.element.xpath(
            'ancestor::fieldset')
        if fieldset:
            return ParsedFieldSet(fieldset[0])

    def get_outer_container(self):
        return ParsedFieldContainer(
            self.element.xpath('ancestor::div[contains(@class,"field")]')[0])


class ParsedFieldSet(ParsedElement):
    def get_contained_field(self):
        """Return a template field suitable for repeating within a
        fieldset
        """
        return self.get_contained_fields()[0]

    def make_template(self, delete_original=True):
        template = deepcopy(self.element.xpath('./*'))
        if delete_original:
            for child in self.element.iterchildren():
                self.element.remove(child)
        return template

    def append_template(self, template):
        for node in deepcopy(template):
            try:
                node.attrib['class'] += " %s" % TEMPLATE_CLASS
            except KeyError:
                pass
            self.element.append(node)

    def clear_template_classes(self):
        for element in self.xpath(
            '//*[contains(@class, "%s")]' % TEMPLATE_CLASS):
            current = element.attrib['class']
            # better with regex?
            current = current.replace(" " + TEMPLATE_CLASS, "")
            current = current.replace(TEMPLATE_CLASS + " ", "")
            element.attrib['class'] = current

    def get_contained_fields(self):
        """Return multiple template fields suitable for repeating
        within a fieldset; by default, remove them from the source
        """
        el = self.element.xpath('descendant::div[contains(@class, "field")]')
        return [ParsedFieldContainer(x) for x in el]

    def get_sequence_name(self):
        marker = self.xpath('input[@type="hidden" '
                            'and @name="__start__" '
                            'and contains(@value, "sequence:")]')[0]
        name = marker.attrib['value'][len("sequence:"):]
        return name


class ParsedFieldContainer(ParsedElement):

    def get_error(self):
        return self.element.xpath(
            'descendant::div[contains(@class, "error-message")]')[0]


class ParsedFormField(ParsedElement):
    """Encapsulates stuff we want to do on an etree-parsed form field
    """

    def set_value(self, value):
        """Set the value of a form field
        """
        # XXX needs extending to support other field types
        value = str(value)
        if self.element.tag == "textarea":
            self.element.text = str(value)
        else:
            self.element.set('value', str(value))
        return self.element

    def get_error(self):
        return self.get_outer_container().get_error()

    def clear_template_class(self):
        container = self.get_outer_container()
        current = container.element.attrib['class']
        current = current.replace(" " + TEMPLATE_CLASS, "")
        current = current.replace(TEMPLATE_CLASS + " ", "")
        container.element.attrib['class'] = current


class ParsedForm(ParsedElement):
    """A simple form which can apply flat data supplied in a dict
    """
    def __init__(self, template=None, data=None):
        self.data = data or {}
        self.schema = schema_registry.get(self.data['schema'],
                                          None)
        self.form = None
        if template:
            self.form = self.consume_template(template)
        super(ParsedForm, self).__init__(element=self.form)

    def validate(self):
        self.validated = get_validated(self.data)
        return self.validated

    def consume_template(self, template):
        self.raw_template = template
        parser = etree.HTMLParser(remove_blank_text=False)
        self.page = etree.fromstring(template, parser=parser)
        form = self.page.xpath('//input[@value="%s"]/..' % self.data['schema'])
        return form[0]

    def transform(self):
        for k, v in self.validated['data'].items():
            el = self.get_field(k)
            error = el.get_error()
            error.text = self.data['errors'].get(k, '')
            el.set_value(v)
        return etree.tostring(self.page)

    def is_valid(self):
        return "errors" not in self.validated

    def __repr__(self):
        return "%s" % etree.tostring(self.form)


class PeppercornForm(ParsedForm):
    """A complex form which can apply structured data in the
    peppercorn format
    """
    START_TAG = '<input type="hidden" name="%s" value="%%s:%%s" />' \
                % START
    END_TAG = '<input type="hidden" name="%s:%%s" />' % END

    def parse_from_peppercorn(self, tuples):
        self.data = {'data': peppercorn.parse(tuples)}

    def render(self, name, data):
        if isinstance(data, types.ListType):
            self.parse_list(name, data)
        elif isinstance(data, types.DictType):
            self.parse_dict(name, data)
        else:
            self.output_field(name, data)

    def output_field(self, name, value):
        field = self.get_field(name)
        if not self.is_valid():
            error = field.get_error()
            fieldset = field.get_outer_fieldset()
            if fieldset:
                # we're in a list
                seq_name = fieldset.get_sequence_name()
                # subtract one to account for the template
                i = len(fieldset.get_fields(name)) - 1
                # XXX this won't currently work for nested lists, this
                # is a hack to deal with common case of lists of dicts
                # one deep
                if seq_name != name:
                    name = "%s.%d.%s" % (seq_name, i, name)
                else:
                    name = "%s.%d" % (name, i)
            error.text = self.data['errors'].get(name, '')
        field.set_value(value)
        field.clear_template_class()

    def parse_list(self, name, list_data):
        # emit start-sequence token
        startnode = etree.fromstring(self.START_TAG % (SEQUENCE,
                                                       name))
        fieldset = self.get_fieldset(name)
        # XXX the following breaks with lists nested two deep -
        # enable test xtest_deeper_peppercorn_validation to start
        # fixing this....
        list_template = fieldset.make_template(delete_original=True)
        fieldset.append(startnode)
        for data in list_data:
            if isinstance(data, types.DictType):
                startnode = etree.fromstring(self.START_TAG % (MAPPING, name))
                fieldset.append(startnode)
            fieldset.append_template(list_template)
            self.render(name, data)
        # emit end-sequence token
        fieldset.append(etree.fromstring(self.END_TAG % name))

    def parse_dict(self, name, dict_data):
        # emit start-sequence token
        fieldset = self.get_fieldset(name)
        for key, data in dict_data.items():
            self.render(key, data)
        # emit end-sequence token
        fieldset.append(etree.fromstring(self.END_TAG % name))

    def transform(self):
        for name, data in self.data['data'].items():
            self.render(name, data)
        return etree.tostring(self.page)
