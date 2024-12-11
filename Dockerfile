FROM python:alpine

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY bot/ bot/
COPY services/ services/
COPY models/ models/

# Set environment to production
ENV ENVIRONMENT=production

# Create non-root user for security
RUN adduser -D botuser && chown -R botuser:botuser /app

# Switch to non-root user
USER botuser

# Command to run the application
CMD ["python", "main.py"]
