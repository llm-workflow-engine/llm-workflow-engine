import gradio as gr
from chatgpt_wrapper import ChatGPT

bot = ChatGPT()


def get_response(message):
    response = bot.ask(message)
    return response


if __name__ == "__main__":
    interface = gr.Interface(fn=get_response, inputs=gr.inputs.Textbox(
        lines=5, label="You"), outputs=gr.outputs.Textbox(label="chatGPT"))
    interface.launch()
