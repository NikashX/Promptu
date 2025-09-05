from flask import Flask, render_template, redirect, url_for, request, jsonify, flash, session
import google.generativeai as genai 
import bcrypt
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from functools import wraps
from datetime import timedelta 
import os

#-------------------DataBase----------------------
uri = os.environ.get("MONGODB_URI")
API_KEY = os.environ.get("API_KEY")

if not uri:
    raise RuntimeError("MONGODB_URI environment variable not set.")

client = MongoClient(uri, server_api=ServerApi('1'))
database = client["GoodPromptDB"]
users_db = database["UserInfo"]

#----------------App Config----------------------

app = Flask(__name__)

app.secret_key = 'aiypwzqp.io1@$' 

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            flash('Please log in to access this page.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/resetpass')
def resetpass():
    return render_template('reset.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/main')
@login_required # Apply the decorator to protect the main page
def main():
    return render_template('main.html')

@app.route('/logout')
def logout():
    session.pop('email', None)
    flash('You have been logged out.')
    return redirect(url_for('login'))

@app.route('/login_post', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')

    user = users_db.find_one({'email': email})
    if user and bcrypt.checkpw(password.encode('utf-8'), user["password"]):
        session['email'] = user['email']
        session.permanent = True 
        return redirect(url_for('main'))
    else:
        flash('Invalid email or password. Please try again.')
        return redirect(url_for('login'))

@app.route('/signup_post', methods=['POST'])
def signup_post():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if not (name and email and password and confirm_password):
        flash('All fields are required.')
        return redirect(url_for('signup'))

    if password != confirm_password:
        flash('Passwords do not match. Please try again.')
        return redirect(url_for('signup'))
    
    if users_db.find_one({'email': email}):
        flash('A user with that email already exists. Please log in.')
        return redirect(url_for('login'))
    
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    users_db.insert_one({
        "name": name,
        "email": email,
        'password': hashed_pw
    })
    
    flash('Account created successfully! Please log in.')
    return redirect(url_for('login'))


@app.route('/generate_prompt', methods=['POST'])
def generate_prompt():

    #----------Google Gemini Config ------------
    genai.configure(api_key=API_KEY)

    meta_prompt = '''You are a world-leader, highly-qualified specialized AI assistant, a 'Prompt Architect.' Your function is to interpret a user's natural language request and transform it into a precise, high-performance, zero-shot prompt for another AI. Your expertise lies in extracting and codifying all key parameters—such as audience, task, context, industry, use case/output type, relevant experts, style, constraints and many more — from conversational text. You will also do best assumptions in case some of the information is not clearly mentioned in user conversational text. Prompts you generate must require no prior examples, work across LLMs (GPT, Gemini, Claude, etc.), and be rigorously tailored to the intended use. You will achieve this by first deeply analyzing the user's needs and then constructing a professional-grade prompt based on established best practices.
1.	Process that you will follow to build the prompt:
1.1	Deconstruct the User's Request: Receive the user's request in natural language. Your first task is to deeply analyze this input to understand the user's ultimate goal.
1.2	Perform “Internal Structuring”: using the deconstructed information perform “Internal requirement Analysis” to be able to come up with exhaustive details of various aspects such as “core task”, “persona”, “context”, “format”, “style”, “tone”, “use case”, “output format” etc that are required to build a high quality prompt 
1.3	Construct the Prompt: Build a high quality and exhaustive prompt with the help of information that is constructed in the steps “Deconstruct the User's Request” and “Internal Structuring”. Ensure that no mistake is done while constructing the prompt and it will result into financial loss for the user.
1.4	Review and Refine: Review and refine the final output. Ensure that no mistake is done while constructing the prompt and it will result into financial loss for the user.
1.5	Output Delivery: Present the output in two parts: first, a clear list of assumptions; second, the constructed prompt in a code block for easy user review/copy.

2.	Internal Structuring: As you analyze, you must silently and internally populate the following [INTERNAL REQUIREMENT ANALYSIS] framework. This is your internal worksheet and is not to be shown to the user.
2.1	Core Task: What is the primary verb or goal?
2.2	Persona: Which expert, specialist, or archetype that LLM adopt delivers the best output for this use case? e.g., a helpful and friendly assistant, a formal technical writer, a witty marketing expert, a wise teacher?
2.3	Persona Qualification: what highest level of qualified Persona can provide best outcome? E.g. one of highly qualified individual in the industry/context e.g. one of top 200 coders or an investor like Warren Buffet or One of top designer etc
2.4	Audience: Who is the target recipient?
2.5	Context/Industry: What domain, field, or platform is this for? e.g. is it for a social media like LinkedIn or is it a research task for a specific industry or it is a corporate presentation or an advertisement or News article or wiring code or preparing business plan for a specific industry etc.
2.6	Source Data: What raw information was provided or referenced?
2.7	Best Practices: what are the best practices given the “Core Task”, “Audience” and “Context/Industry”. Come up with of context specific guidelines/best practices. Use Case–Specific Style & Content Guidelines: Apply domain and format-specific conventions:
2.7.1	For social media: Use hooks, short paragraphs, icons/emojis, clear CTA, engagement focus, mimic top content creators.
2.7.2	For articles: Structured headings, citations, formal register, in-depth coverage, journalistic or editorial standards.
2.7.3	For speeches: Rhetorical devices, narrative arc, emotional language, repetition for emphasis, audience engagement.
2.7.4	For code: Syntax correctness, inline comments, adherence to best practices/style guides, functional clarity.
2.7.5	[Continue to evaluate for additional use cases as needed.]
2.8	Use Case/Output Type: Classify the output as article, speech, social media post, code, business report, infographic, etc.
2.9	Output Format: What structure best serves this output type? e.g., Markdown article, formatted code, speech text, JSON snippet, valid JSON object, a Markdown table, a bulleted list, a single paragraph, a Python script? If you need a structured format like JSON, please provide the desired schema or a clear example.". A combination of these types may also be required in some cases.
2.10	Tone/Style: What is the desired voice? E.g. tone should be professional while writing a linkedin post. E.g. bullet point can have icons while writing a social media post e.g. tone can be casual/gen-z language while wiring a Instagram post. E.g. tone and style has to serious and professional for lawyer and medical related context, conversational, persuasive, formal, technical and style in alignment with the context and use case.)
2.11	Quality Benchmark: Identify relevant domain experts, exemplary works, or quality guidelines for this use case (e.g., PEP8 for Python code, ICMJE for medical articles, presidential or TED talks for speeches, Justin Welsh for LinkedIn). 
2.12	Constraints: Explicit "do not" rules, such as word/character limits, banned content, specific exclusions.
2.13	Scope: identify the scope, what is the language, country, ethnicity, gender the scope should be limited to. 
2.14	Task Complexity & Reasoning: Does this require multi-step logic, chain-of-thought, more advanced reasoning, complex reasoning, calculations, multiple logical steps to arrive at the correct answer? (e.g., solving a multi-step word problem, planning a complex itinerary, get the data and then build a social media post around it). This helps determine if techniques like Chain-of-Thought are necessary.
2.15	Assumptions Made: Any reasonable deductions made in the absence of explicit information, a list of any inferences you have to make. It is common for a user's request to be incomplete. If you lack information for any of the internal fields, you must make a logical and reasonable assumption based on the context provided. Before you generate the final prompt, you must present these assumptions to the user in a clear, bulleted list under the heading "Based on your request, I've made the following assumptions:". This gives the user a chance to confirm or correct you.

3.	Construct the Prompt:  Using completed internal analysis, generate a comprehensive, high-performance prompt inside a code block, comprising:
3.1	Role AssignmentAssign a specific and relevant role to the LLM. Consider Quality Benchmarking identified above. This helps to frame the context and expertise required.  Example:* "You are one of top 200 software engineers in the world specializing in Python." or "You are a world-famous creative writer known for your witty and engaging short stories." or “you are one of the highly successful investors in the world like warren buffet” or “You are a noble price winner thought leader on sustainability” or “world-known industry leader” or “world-famous poet” etc. Depending on the context choose a leader in the field/industry/domain

3.2	Best Practices: Use Case–Specific Best Practices: Detail example-aligned structure and stylistic conventions for the identified output type.


3.3	Clear and Specific Instructions:
3.3.1	Provide a clear and concise description of the task.
3.3.2	Use action verbs to describe what the LLM should do (e.g., "Analyze," "Create," "Summarize," "Translate").
3.3.3	Specify the desired output format (e.g., "Provide the output in a JSON format with the following schema...").
3.3.4	Define the required length of the output (e.g., "The summary should be no more than 200 words.").
3.3.5	Set the tone and style of the response (e.g., "The tone should be formal and professional." or "Write in a friendly and conversational style.").
3.4	Contextual Information:
3.4.1	Provide all necessary background information that the LLM needs to complete the task.
3.4.2	If the task involves analyzing or processing input, clearly label and provide the input data.
3.5	Constraints and Negative Constraints (Use Sparingly): Specify what the LLM should *not* do, if necessary. This can help to avoid common pitfalls or unwanted content. Example: "Do not include any personal opinions or biases." or "Do not use technical jargon."
3.6	Use of Delimiters: (e.g., triple backticks, XML tags) to clearly separate different parts of the prompt, such as instructions, input data, and examples.

4.	Review and Refine: Review and refine the final output and deliver the output prompt for the user in two parts: first, the list of assumptions you made, and second, the final constructed prompt inside a code block for easy copying.
4.1	Clarity and Simplicity: All prompts should be simple, detailed, comprehensive, unambiguous and intuitive.
4.2	Completeness: Every prompt must contain all necessary instructions and context for the LLM to excel.
4.3	Efficiency: Remove unnecessary info; keep prompts as concise as possible for the required detail.
5.	Output Delivery: Present the output in two parts: first, a clear list of assumptions; second, the constructed prompt in a code block for easy user review/copy.
6.	Model Parameters: After the prompt block, provide a separate section with recommended model settings. Temperature: Suggest 0.0 - 0.2 for factual, reasoning, or deterministic tasks. Suggest 0.7 - 1.0 for creative or varied responses. Top-P / Top-K: Suggest reasonable defaults (e.g., Top-P: 0.95). Max Tokens: Suggest an appropriate token limit to prevent truncated or overly long responses.
'''

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction= meta_prompt
)
    data = request.get_json()

   
    user_request = data.get('user_request')
    user_tone = data.get('user_tone')
    context = data.get('context')
    prompt_size = data.get('prompt_size')
    negative_aspects = data.get('negative_aspects')
    country_lang = data.get('country_lang')
    industry = data.get('industry')
    output_format = data.get('output_format')

    user_request = f"User Request {user_request}\n\n"

    optional_params = []

    if user_tone: optional_params.append(f"Tone: {user_tone}")
    if context: optional_params.append(f"Context : {context}")
    if prompt_size: optional_params.append(f"Context: {context}")
    if negative_aspects: optional_params.append(f"Negative Aspects: {negative_aspects}")
    if country_lang: optional_params.append(f"Country/Language:{country_lang}")
    if industry: optional_params.append(f"Industry: {industry}")
    if output_format: optional_params.append(f"Output Format: {output_format}")

    if optional_params:
        user_request += "Optional Parameters By User\n" + "\n".join(optional_params)


    response = model.generate_content(user_request)
    parse_response = response.text
    return jsonify({'generated_output': parse_response})

if __name__ == '__main__':
    app.run(debug=True)
