

class AttributeCollection(object):

    def __init__(self, attributes_table, plugin_data):
        self.attributes_table = attributes_table
        self.set_attributes(plugin_data)

    def set_attributes(self, plugin_data):

        for attribute in self.attributes_table:

            details = self.attributes_table[attribute]
            value = plugin_data.get(attribute, details.get("default_value"))
            if details.get("type"):
                try:
                    value = details["type"](value)
                except:
                    pass

            setattr(self, attribute, value)

    def get(self, attribute, default_value=None):
        try:
            return getattr(self, attribute)
        except AttributeError:
            return default_value

    def to_dict(self):
        return self.attributes_table
