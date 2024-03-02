import openai
import pyttsx3
import atexit
import speech_recognition as sr
import os
from prompt import system_content, user_content


# Maximum number of tokens in response generated by ChatGPT
MAX_TOKEN = 100

# Token limit in conversation history before 
TOKEN_LIMIT = 3000

# Number of user-assistant content pairs to clear once conversation limit has been reached.
CLEAR_PAIRS = 10

# Log conversation history into /conversation_log/conversation.txt 
CONVERSATION_PATH = os.path.join("conversation_log", "conversation.txt")


class TextChat(object):
    def __init__(self, max_token=MAX_TOKEN) -> None:
        """
        Initialise text-prompted ChatGPT by setting the system content. 
        """
        self.max_token = max_token

        # Initialise text-to-speech engine
        self.ENGINE = pyttsx3.init()

        # List keeping track of conversation history
        self.conversation = []

        # Register save_conversation function to log conversation history when program terminates
        atexit.register(self.save_conversation)
    
        # Add initial instructions to conversation to configure ChatGPT characteristics
        self.conversation.append(
            {"role": "system", "content": system_content}
        )
        self.conversation.append(
            {"role": "user", "content": user_content}
        )

        completion = openai.ChatCompletion.create(
            model = "gpt-3.5-turbo",
            messages = self.conversation,
            max_tokens = self.max_token
        )

        output = completion["choices"][0]["message"]["content"]

        print(f"Initial response: {output}")
        print("ChatGPT initialised.")


    def get_prompt(self):
        """
        Gets user prompt through manual command line input. Returns the prompt as a string
        """
        prompt = input("Prompt: ")
        return prompt.lower()


    def get_response(self, prompt):
        """
        Connect to ChatGPT to generate a response to given prompt together with context from conversation history.
        Returns a string.
        """
        if prompt is None:
            print("No prompt given.")
            return

        # Add prompt to conversation as user message
        self.conversation.append({"role": "user", "content": prompt})

        completion = openai.ChatCompletion.create(
            model = "gpt-3.5-turbo",
            messages = self.conversation,
            max_tokens = self.max_token
        )

        output = completion["choices"][0]["message"]["content"]
        print(f"Response: {output}")

        tokens = completion["usage"]["total_tokens"]
        print(f"Total tokens used: {tokens}")

        # Remove some conversation history to avoid exceeding maximum token limit of model 
        if tokens > TOKEN_LIMIT:
            self.clear_conversation(self.conversation)

        # Log user message into conversation history 
        self.conversation.append({"role": "assistant", "content": output})

        return output


    def clear_conversation(self, prompts=CLEAR_PAIRS):
        """
        Function to clear conversation history with ChatGPT. Clears first 'prompts' number of user-assistant content pairs.
        """
        # Account for user-assistant content pair
        end_index = (2 * prompts) + 2
        for i in range(2, end_index):
            del self.conversation[i]


    def check_wellbeing(self):
        """
        Function to prompt ChatGPT to ask elderly question to check in on their well-being
        """
        output = self.get_response("Ask me the question: Are you okay?")
        self.speak(output)


    def speak(self, text):
        """
        Takes a string as input and uses the text-to-speech engine to speak the text
        """
        if text is None:
            return
        
        self.ENGINE.say(text)
        self.ENGINE.runAndWait()

    
    def save_conversation(self):
        """
        Logs conversation in a text file.
        """
        with open(CONVERSATION_PATH, "a") as f:
            f.write("Start of Converstaion. \n")
            for speech in self.conversation:
                f.write(f"{speech}\n")
            f.write("End of Conversation. \n\n")


class VoiceChat(TextChat):
    def __init__(self, source) -> None:
        """
        Initialise voice-prompted ChatGPT. Source must be a sr.Microphone() object 
        """
        assert isinstance(source, sr.Microphone), "Audio input must be of class sr.Microphone."

        self.source = source

        #  Obtain voice recogniser from microphone
        self.recogniser = sr.Recognizer()

        # Below are the configurations for the voice recogniser

        self.recogniser.energy_threshold = 4000
        
        # Adjusts the energy threshold dynamically using audio from source to account for ambient noise
        # Duration parameter is the maximum number of seconds that it will dynamically adjust the threshold for before returning.       
        self.recogniser.adjust_for_ambient_noise(self.source, duration=0.5)

        # Represents the minimum length of silence (in seconds) that will register as the end of a phrase. 
        # Smaller values result in the recognition completing more quickly, but might result in slower speakers being cut off.
        self.recogniser.pause_threshold = 0.5

        super().__init__()

    def get_prompt(self):
        """
        Gets user prompt through voice recognition. Returns the prompt as a string
        """
        try:
            # Listens for the user's input
            print("Listening...")
            audio = self.recogniser.listen(self.source)
            
            # Use Google Speech Recognition to recognize audio
            prompt = self.recogniser.recognize_google(audio)
            prompt = prompt.lower()
            print(f"Speech input: {prompt}")
            return prompt

        except sr.RequestError as e:
            print(f"Could not request results: {e}")
        
        except sr.UnknownValueError:
            print("No speech detected.")
            return 