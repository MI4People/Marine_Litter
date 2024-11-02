FROM python:3.9-slim

WORKDIR /marine_litter

COPY requirements.txt .

RUN pip indtall --no-cache-dir -r requirements.txt

CMD [ "python", "./download.py" ]