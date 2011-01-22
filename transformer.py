from lxml import etree
import schemaish
from validatish import validator


schema_registry = {}
                          
def get_validated(data):
    schema = schema_registry.get(data['schema'])
    try:
        schema.validate(data['data'])
    except schemaish.Invalid, e:
        errors = {}
        for k, v in e.error_dict.items():
            errors[k] = v.message
        data['errors'] = errors
    return data


def apply_validated_data(content, data):
    parser = etree.HTMLParser(remove_blank_text=True)
    tree = etree.fromstring(content, parser=parser)
    form = tree.xpath('//input[@value="%s"]/..' % data['schema'])
    form = form[0]
    for k, v in data['data'].items():
        matching_elements = []
        input_xpath = '//input[@name="%s"]' % k
        textarea_xpath = '//textarea[@name="%s"]' % k
        for xpath in [input_xpath,
                      textarea_xpath]:
            match = form.xpath(xpath)
            if match:
                if len(match) > 1:
                    raise Exception(
                        "More than one form element with name '%s'" % k)
                matching_elements.append(match[0])
        if len(matching_elements) > 1:
            raise Exception(
                "More than one form element with name '%s'" % k)
        for el in matching_elements:
            error = el.xpath('../div[@class="error-message"]')[0]
            error.text = data['errors'].get(k, '')
            if el.tag == "textarea":
                el.text = str(v)
            else:
                el.set('value', str(v))
    return etree.tostring(form)
