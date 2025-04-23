WORKFLOW_OPTIMIZE_PROMPT = """I am building a vqa agent. 
My intuition is that the current hindrance of mllm's vqa capability is the over-abundance of visual information in an image.
By cropping and spawning subagents, we can trim down the information, to focus and to split task into managable parts.
Referring to the given graph and prompt, which forms a basic example of a vqa agent, 
please reconstruct and optimize them. You can add, modify, or delete functions, parameters, or prompts. Include your 
single modification in XML tags in your reply. Ensure they are complete and correct to avoid runtime failures. When 
optimizing, you can incorporate critical thinking methods like review, revise, ensemble (generating multiple answers through different/similar prompts, then voting/integrating/checking the majority to obtain a final answer), selfAsk, etc. Consider 
Python's loops (for, while, list comprehensions), conditional statements (if-elif-else, ternary operators), 
or machine learning techniques (e.g., linear regression, decision trees, neural networks, clustering). The graph 
complexity should not exceed 10. Use logical and control flow (IF-ELSE, loops) for a more enhanced graphical representation.
Output the modified graph and all the necessary Prompts in prompt.py (if needed).
The prompt you need to generate is only the one used in `XXX_PROMPT` within Custom. Other methods already have built-in prompts and are prohibited from being generated. Only generate those needed for use in `prompts`; please remove any unused prompts in `prompts`.
the generated prompt must not contain any placeholders.
Considering information loss, complex graphs may yield better results, but insufficient information transmission can omit the solution. It's crucial to include necessary context during the process."""

WORKFLOW_OPTIMIZE_PROMPT = WORKFLOW_OPTIMIZE_PROMPT.format(category='vqa')


WORKFLOW_INPUT = """
Here is a graph and the corresponding prompt (prompt only related to the custom method) that performed excellently in a previous iteration (maximum score is 1). You must make further optimizations and improvements based on this graph. The modified graph must differ from the provided example, and the specific differences should be noted within the <modification>xxx</modification> section.\n
<sample>
    <experience>{experience}</experience>
    <modification>(such as:add /delete /modify / ...)</modification>
    <score>{score}</score>
    <graph>{graph}</graph>
    <prompt>{prompt}</prompt>
    <operator_description>{operator_description}</operator_description>
</sample>
we use a custom subclass of str so str.format can take in Image.Image as well as str. 
Below are the logs of some results with the aforementioned Graph that performed well but encountered errors, which can be used as references for optimization:
{log}

First, provide optimization ideas. **Only one detail point can be modified at a time**, and **no more than 5 lines of code may be changed per modification**—extensive modifications are strictly prohibited to maintain project focus!
Sometimes it is a very good idea to shrink code and remove unnecessary steps. 
When introducing new functionalities in the graph, please make sure to import the necessary libraries or modules yourself, except for operator, prompts, which have already been automatically imported.
**Under no circumstances should Graph output None for any field.**
"""

WORKFLOW_CUSTOM_USE = """\nHere's an example of using the `custom` method in graph:
```
# You can write your own prompt in <prompt>XXX_PROMPT="your_prompt"</prompt> and then use it in the Custom method in the graph
response = await self.custom(input=problem + self.prompts['XXX_PROMPT'])
# You can also concatenate previously generated multimodal results in the input to provide more comprehensive contextual information.
# response = await self.custom(input=problem+f"xxx:{xxx}, xxx:{xxx}", instruction=XXX_PROMPT)
# The output from the Custom method can be placed anywhere you need it, as shown in the example below
solution = await self.custom(input=f"question:{problem}, xxx:{response['response']}")
```
Note: In custom, the input and instruction are directly concatenated(instruction+input), and placeholders are not supported. Please ensure to add comments and handle the concatenation externally.\n

**Introducing multiple operators at appropriate points can enhance performance. If you find that some provided operators are not yet used in the graph, try incorporating them.**
"""

OPERATOR_DESCRIPTION = "{id}. {name}: {description}, with interface {interface} \n"