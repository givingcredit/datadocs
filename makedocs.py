import os, shutil
from jinja2 import Environment, PackageLoader
import yaml
import os.path
import json
import markdown

class FieldError(Exception):
    """
    Class to inform the user of a field error in her or
    his yaml configuration.
    """
    def __init__(self, section, field):
        self.section = section
        self.field = field
        self.value = "%s field in the %s section (is the %s field missing?)" % (self.field, self.section, self.field)
    def __str__(self):
        return repr(self.field)
    
class Group():
    def __init__(self, title, description):
        self.title = title
        self.description = description
        self.sections = []

    def add_section(self, section):
        self.sections.append(section)

class Section():
    """

    Args:
        name (String)               Name of the section
        title (String)               Section title
        description (String)         Description
    """
    def __init__(self, name, title, description):
        self.name = name
        self.title = title
        self.description = description
        self.tables = []

    def addTable(self, table):
        """
        Add a table object to the table list.
        Args:
            table (Table)    Table object
        """
        self.tables.append(table)

    def getFieldNames(self):
        """
        Returns a list of field names in this section
        """
        fieldNames = []
        for table in self.tables:
            for field in table.fields:
                fieldNames.append(field.name)
        return fieldNames

    def getHtmlName(self, appendText=None):
        """
        Returns a string taking the file name and turning it into a
        reasonable html file name that strips white space

        Args:
            appendText      String optional text to append to the end of the
                            html file name.
        """
        htmlName = self.name.replace(' ', '_').lower()
        htmlName += '.html'
        return htmlName

    def addUncategorizedFields(self, df):
        """
        Adds all fields that have not been documented by the user
        to a table called "Uncategorized" and add the
        table to this section.

        Args:
            df    Pandas dataframe.
        """

        # create an uncategorized table
        uncategorized = Table("Uncategorized", "Autogenerated list of fields that have not been documented.")
        documentedFieldNames = self.getFieldNames()

        for fieldName in list(df.columns.values):
            if fieldName not in documentedFieldNames:
                # this field name is not documented, so
                # let's add it to the list of uncategorized
                # fields
                field = Field(fieldName)
                field.dataType = field.getDataType(df)

                # add the field to the table
                uncategorized.addField(field)

        # add the table
        self.addTable(uncategorized)

    def printSelectAll(self, language = "R"):
        """
        Prints code in the specified language that selects all fields
        in this section.

        Args:
            language    String indicating the language to select all variables in.
        """
        code = ""
        if language.lower() == "r":

            # TODO: fix last comma issue

            code += "c(\n"

            for table in self.tables:
                code += "   # %s\n" % table.title

                for field in table.fields:
                    code += '   "%s",\n' % field.name
            code += ")"
        elif language.lower() == "python":

            code += "[\n"
            for table in self.tables:
                code += "   # %s\n" % table.title

                for field in table.fields:
                    code += '   "%s",\n' % field.name
            code += "]"

        return code
    
    def render(self, groups):
        env = Environment(loader=PackageLoader('makedocs', 'templates'))
        template = env.get_template('section.html')
        file = open('site/%s' % (self.getHtmlName()), 'w')

        # check if there is an [file_name].md file in /docs. If there is
        # open it up, convert the markdown contents and pass it along as
        # content
        try:
            content = markdown.markdown(open('docs/' + self.name + '.md', 'r').read())
        except:
            content = None

        file.write(template.render(section=self, static="static", home="index.html",
            content=content, groups=groups))

class Table():
    """
    A table holds any number of fields in a section
    """
    def __init__(self, title, name, description = None):
        """
        Args:
            title           Friendly table title
            name            Name of the table in the database
            description     String description
        """
        self.title = title
        self.name = name
        self.description = description
        self.fields = []

    def addField(self, field):
        self.fields.append(field)

class Field():
    """
    A field in a section.
    """
    def __init__(self, name, data_type, description, private=False):
        """
        Args:
            name (String):          Field name in the section
            data_type (String):     Data type
            description (String):   Field description
            private (Boolean):      Boolean indicating if a field is private or public
        """
        self.name = name
        self.description = description
        self.data_type = data_type
        self.private = private

def generateSearch(sections):
    """
    Generates a JSON file that allows users to search fields across sections.

    Args:
        sections    A list of section objects.
    Return:
        Returns a JSON file that is a list of dictionaries, where
        each dictionary defines a field.
    """

    search = []

    for section in sections:
        tableNumber = 1
        for table in section.tables:
            fieldNumber = 1
            for field in table.fields:
                search.append({
                    "field" : field.name,
                    "description": field.description,
                    "table" : table.title,
                    "section" : section.title,
                    "field_link" : "%s#field-%d-%d" % (section.getHtmlName(), tableNumber, fieldNumber),
                    "table_link" : "%s#table-%d" % (section.getHtmlName(), tableNumber),
                    "section_link" : "%s" % (section.getHtmlName())
                })
                fieldNumber += 1
            tableNumber += 1

    # return as json
    return json.dumps(search)

if __name__ == "__main__":
    """
    Loop through every section in the datadocs yaml
    file.
    """

    # remove the /docs dir if it exists
    if os.path.exists("site"):
        shutil.rmtree('site')
    # if docs doesn't exist, which it shouldn't, make it again
    if not os.path.exists('site'):
        os.makedirs('site')

    # get the data docs settings
    datadocs = yaml.load(open("docs/datadocs.yaml", "r"), Loader=yaml.Loader)

    groups = []
    for g in datadocs['groups']:
        group = Group(title=g['title'], description=g['description'])


        for s in g['sections']:

            # open the section yaml
            section_yaml = yaml.load(open("docs/" + s + ".yaml", "r"), Loader=yaml.Loader)

            # create a section object
            section = Section(name=s, title=section_yaml['title'], description=section_yaml['description'])

            for t in section_yaml['tables']:
                # create a table object
                table = Table(t['title'], t['name'], t['description'])
                if 'fields' in t:
                    for f in t['fields']:

                        private = False
                        if 'private' in f:
                            private = f['private']

                        field = Field(name=f['name'], description=f['description'], private=private, data_type=f['type'])

                        # add this field to the table
                        table.addField(field)

                # add this table to the section
                section.addTable(table)

            group.add_section(section)
        
        groups.append(group)

    # generate search index
    #search = generateSearch(sections)
    #open('site/search.json', 'w').write(search)

    """
    Render templates
    """
    # jinja2 templating settings
    env = Environment(loader=PackageLoader('makedocs', 'templates'))

    # make index page
    template = env.get_template('home.html')
    file = open('site/index.html', 'w')

    # render sections
    for group in groups:
        for section in group.sections:
            section.render(groups)

    # check if there is an index.md file in /docs. If there is
    # open it up, convert the markdown contents and pass it along as
    # content
    try:
        content = markdown.markdown(open('docs/index.md', 'r').read())
    except:
        content = None
    file.write(template.render(groups=groups, static="static", home="index.html", content=content))


    # copy static folder (css and images)
    shutil.copytree("static", "site/static")
