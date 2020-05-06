# urban dictionary plugin
# author: adrift
#
# usage:
# .urban, .ud [PHRASE]              -- ask urban dictionary to
#                                      define phrase

from core import hook

import json
import urllib

@hook.hook('command', ['ud', 'urban'])
async def urban(client, data):

    # sets the index for which definition to query
    definition_index = 0

    max_response_length = 405

    query = ''
    split = data.split_message

    # empty query
    if not split:
        return
     
    # if user is specifiying a definition index specific parsing is required
    if split[-1].isnumeric():
        # query should not have last word, which indicates definition index
        query = ' '.join(split[:-1])
        definition_index = int(split[-1])
    else:
        query = ' '.join(split)

    urban_dictionary_url = "https://api.urbandictionary.com/v0/define?term="
    word_to_define = urllib.parse.quote(query)
    request_url = urban_dictionary_url + word_to_define

    try:
        definitions = urllib.request.urlopen(request_url)
    except urllib.error.HTTPError:
        asyncio.create_task(client.message(data.target, "HTTP error."))
        return

    definitions = urllib.request.urlopen(request_url)
    j_definitions = json.load(definitions)

    # no definitions
    if not j_definitions["list"]:
        asyncio.create_task(client.message(data.target, "No definitions available."))
        return

    # try to see if request definition index is out of range
    try:
        definition_list = j_definitions["list"][definition_index]
    except IndexError:
        asyncio.create_task(client.message(data.target, "Definition index out of range."))
        return

    definition_list = j_definitions["list"][definition_index]
    definition = definition_list["definition"].replace('\n', ' ')
    example = definition_list["example"].replace('\n', ' ')
    definition_no_brackets = definition.replace('[', '').replace(']', '')
    example_no_brackets = example.replace('[', '').replace(']', '')

    # api caps at 10 definitions, which is why 10 is hardcoded
    urban_response = "[" + str(definition_index) + "/10] " + "\02" + definition_list["word"] + ": \02" + definition_no_brackets + " - " + example_no_brackets

    # trim response length as necessary
    if len(urban_response) > max_response_length:
        asyncio.create_task(client.message(data.target, urban_response[:max_response_length] + '...'))
    else:
        asyncio.create_task(client.message(data.target, urban_response))

    return
