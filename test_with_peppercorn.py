from unittest import TestCase
from lxml import etree
import schemaish
from validatish import validator
import transformer
from transformer import get_validated
from transformer import PeppercornForm


class TestCase(TestCase):
    def test_sequence_peppercorn(self):
        schema = schemaish.Structure()
        urls = schemaish.Sequence(
            attr=schemaish.String(
                validator=validator.URL()))
        schema.add('urls', urls)
        transformer.schema_registry = {'myschema': schema}
        example = {'schema': 'myschema',
                   'data': {
                       'urls': [3, "http://www.com"]}}
        validated_data = get_validated(example)
        self.assertEqual({'data': {'urls': [3, 'http://www.com']},
                          'errors': {'urls.0': 'must be a url'},
                          'schema': 'myschema'},
                         validated_data)
        form = open("form_template.html").read()
        form = PeppercornForm(form, data=validated_data)
        form.validate()
        rendered = etree.fromstring(form.transform())
        expected = rendered.xpath('//input[@name="urls"]')
        self.assertEqual(expected[0].attrib['value'], "3")
        self.assertEqual(expected[1].attrib['value'],
                         "http://www.com")
        error = rendered.xpath('//div[@class="error-message"]')
        self.assertEqual(error[0].text, "must be a url")
        self.assertEqual(error[1].text, None)

    def test_structure_peppercorn(self):
        schema = schemaish.Structure()
        person = schemaish.Structure()
        person.add('name', schemaish.String())
        person.add('age', schemaish.Integer())
        people = schemaish.Sequence(attr=person)
        schema.add('people', people)
        transformer.schema_registry = {'myschema': schema}

        example = {'schema': 'myschema',
                   'data': {
                       'people': [{'name':'zephania',
                                   'age':24},
                                  {'name':'methusula',
                                   'age':133}]
                       }
                   }

        validated_data = get_validated(example)
        form = open("form_structure_template.html").read()
        form = PeppercornForm(form, data=validated_data)
        form.validate()
        rendered = etree.fromstring(form.transform())
        expected = rendered.xpath('//input[@name="name"]')[0]
        self.assertEqual(expected.attrib['value'],
                         'zephania')
        expected = rendered.xpath('//input[@name="age"]')[1]
        self.assertEqual(expected.attrib['value'],
                         '133')

    def test_structure_peppercorn_validation(self):
        schema = schemaish.Structure()
        person = schemaish.Structure()
        person.add('name', schemaish.String())
        person.add('age', schemaish.Integer(validator=validator.Required()))
        people = schemaish.Sequence(attr=person)
        schema.add('people', people)
        transformer.schema_registry = {'myschema': schema}

        example = {'schema': 'myschema',
                   'data': {
                       'people': [{'name':'zephenia',
                                   'age':24},
                                  {'name':'methusula',
                                   'age':None}]
                       }
                   }

        validated_data = get_validated(example)
        form = open("form_structure_template.html").read()
        form = PeppercornForm(form, data=validated_data)
        form.validate()
        rendered = etree.fromstring(form.transform())
        expected = rendered.xpath('//*[@class="error-message"]')[3]
        self.assertEqual(expected.text, 'is required')

    def xtest_deeper_peppercorn_validation(self):
        schema = schemaish.Structure()
        person = schemaish.Structure()
        person.add('name', schemaish.String())
        person.add('numbers',
                   schemaish.Sequence(
                       attr=schemaish.Integer(
                           validated=validator.Integer()
                           )
                       )
                   )
        people = schemaish.Sequence(attr=person)
        schema.add('people', people)
        transformer.schema_registry = {'myschema': schema}

        example = {'schema': 'myschema',
                   'data': {
                       'people': [{'name':'bob',
                                   'numbers': [1, 2, 3]},
                                  {'name':'sue',
                                   'numbers': [9, 7, "frob"]}]
                       }
                   }

        validated_data = get_validated(example)
        form = open("form_deep_structure_template.html").read()
        form = PeppercornForm(form, data=validated_data)
        form.validate()
        # XXX the following fails because nested lists end up copying
        # templates when they shouldn't -- see 'parse_list' method of
        # transformer
        rendered = etree.fromstring(form.transform())
        expected = rendered.xpath('//*[@class="error-message"]')[3]
        self.assertEqual(expected.text, 'is required')

    def test_different_schema_types(self):
        schema = schemaish.Structure()
        transformer.schema_registry = {'myschema': schema}
        example1 = {'schema': 'myschema',
                   'data': {}}
        example2 = {'schema': schema,
                   'data': {}}
        # both of these should work
        get_validated(example1)
        get_validated(example2)

    def runTest(self):
        self.test_something()

if __name__ == "__main__":

    test = TestCase()
    test.runTest()
