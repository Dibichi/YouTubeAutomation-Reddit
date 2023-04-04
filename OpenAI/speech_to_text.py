import whisper
import os
import pandas as pd
from timeit import default_timer as timer


MODEL = "medium"


def correct_subs(script, subs):
    script_counter = 0
    script = script.split()

    for timestamp in subs:
        text = timestamp[1].strip()
        words = text.split()
        subs_counter = 0
        for _ in range(words.length):
            if (words[subs_counter] != script[script_counter]):
                words[subs_counter] = script[script_counter]

            # clause for checking splitting of one word into two wrong words might be needed

            words[subs_counter] = words[subs_counter].replace(",", "").replace(".", "")
            subs_counter += 1
            script_counter += 1
        
        print(words)

def create_srt(file_input, time_offset=0):
    model = whisper.load_model(MODEL)
    result = model.transcribe(file_input)

        # create Subtitle dataframe, and save it
    dict1 = {'start':[], 'end':[], 'text':[]}

    for i in result['segments']:
        dict1['start'].append(i['start'] + time_offset)
        dict1['end'].append(i['end'] + time_offset)
        dict1['text'].append(i['text'].strip().replace(",", "").replace(".", ""))
    """
    df = pd.DataFrame.from_dict(dict1)
    print(df)
    """
    #df.to_csv(f'experiments/{name}/subs.csv')
    subs = list(zip(list(zip(dict1['start'], dict1['end'])), dict1['text']))
    return subs

def create_srt_file(file_input,  output_dir, output_format):
    command = f"whisper {file_input} --model {MODEL} -o {output_dir} -f {output_format}"
    os.system(command)
