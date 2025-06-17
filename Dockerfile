# Use an official pytorch image
FROM pytorch/pytorch:2.1.1-cuda12.1-cudnn8-runtime

# Update  pip
RUN pip install --upgrade pip

# Install system dependencies
RUN apt-get update && apt-get install -y gcc ffmpeg libsm6 libxext6 && rm -rf /var/lib/apt/lists/*

# RUN apt-get update && apt-get install -y git && \
#     rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /project

# Copy project files
COPY requirements.txt .

# Install requirements packet
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . /project/

# Expose port
EXPOSE 8000

# Set PYTHONPATH
ENV PYTHONPATH=/project
  

# Run the app
CMD ["python", "./backend/main.py"]


