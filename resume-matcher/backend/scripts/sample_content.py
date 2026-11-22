"""100% synthetic sample data. All names, emails, phone numbers and companies are fictional."""

JOB_DESCRIPTIONS = {
    "python_developer": """Job Title: Senior Python Developer

About the Role
We are looking for a Senior Python Developer to design, build and maintain scalable backend services
for our recruitment analytics platform.

Key Responsibilities
- Design and develop RESTful APIs and microservices using Python and FastAPI or Django
- Build and optimize PostgreSQL database schemas and complex SQL queries
- Containerize applications with Docker and deploy them to AWS
- Write unit and integration tests with pytest and maintain CI/CD pipelines
- Collaborate with frontend engineers and mentor junior developers
- Monitor performance and improve reliability of production systems

Required Skills
- Python, FastAPI, Django, REST API, PostgreSQL, SQL, Docker, Git, pytest

Preferred Skills
- AWS, Redis, Celery, Kubernetes, CI/CD, React

Experience
- 4+ years of professional experience in backend development with Python

Education
- Bachelor's degree in Computer Science, Information Technology or a related field
""",
    "data_scientist": """Job Title: Data Scientist

Job Summary
Join our analytics team to turn hiring and workforce data into actionable insights and
predictive models.

Responsibilities
- Perform exploratory data analysis and statistical analysis on large datasets
- Build, evaluate and deploy machine learning models for classification and forecasting
- Develop feature engineering pipelines with Python, pandas and NumPy
- Create dashboards and data visualizations to communicate insights to stakeholders
- Design and analyze A/B tests and apply hypothesis testing
- Write efficient SQL queries to extract and transform data

Required Skills
- Python, pandas, NumPy, scikit-learn, Machine Learning, Statistics, SQL, Data Visualization

Nice to Have
- Tableau or Power BI, Apache Spark, Deep Learning, AWS, Time Series

Experience
- 3-6 years of experience in data science or analytics

Education
- Master's degree in Statistics, Mathematics, Computer Science or Data Science
""",
    "ai_ml_engineer": """Job Title: AI/ML Engineer

Overview
We are hiring an AI/ML Engineer to build NLP and deep learning systems that power semantic search
and document understanding.

What You'll Do
- Design, train and fine-tune deep learning models using PyTorch or TensorFlow
- Build NLP pipelines with transformers, embeddings and large language models
- Implement semantic search with sentence embeddings and vector databases
- Deploy and serve models in production using Docker, Kubernetes and MLOps practices
- Evaluate models with rigorous cross-validation and monitor model performance
- Collaborate with data engineers and product teams

Requirements
- Python, PyTorch, TensorFlow, Deep Learning, NLP, Transformers, Machine Learning, Docker

Preferred Qualifications
- LLMs, Vector Databases, MLOps, Kubernetes, AWS, Computer Vision

Experience
- 3+ years of hands-on experience building machine learning systems

Education
- Bachelor's or Master's degree in Computer Science, Artificial Intelligence, Data Science or related field
""",
}

# Each resume: target profile documented in "_profile" (not rendered)
RESUMES = [
    {
        "_file": "01_aarav_mehta_senior_python.pdf", "_profile": "STRONG match - Python Developer",
        "name": "Aarav Mehta", "email": "aarav.mehta@example.com", "phone": "+91 98765 43210",
        "summary": "Senior Python developer with 6+ years of experience building scalable REST APIs and "
                   "microservices with FastAPI and Django, PostgreSQL and AWS.",
        "experience": [
            ("Senior Python Developer", "CloudNova Technologies", "Jan 2022 - Present", [
                "Designed and built RESTful microservices with FastAPI serving 2M requests/day",
                "Optimized PostgreSQL queries and schemas, reducing latency by 40%",
                "Containerized services with Docker and deployed to AWS ECS with GitHub Actions CI/CD",
                "Mentored 4 junior developers and led code reviews"]),
            ("Python Developer", "ByteForge Solutions", "Jun 2019 - Dec 2021", [
                "Developed Django REST Framework APIs for an HR analytics product",
                "Implemented background jobs with Celery and Redis",
                "Raised test coverage to 90% using pytest"]),
            ("Junior Software Engineer", "Infosphere Labs", "Jul 2018 - May 2019", [
                "Built internal tools in Python and SQL"]),
        ],
        "skills": "Python, FastAPI, Django, Flask, REST API, PostgreSQL, SQL, Redis, Celery, Docker, "
                  "Kubernetes, AWS, Git, pytest, CI/CD, Linux",
        "education": [("B.Tech in Computer Science", "National Institute of Technology Trichy", "2014 - 2018")],
        "projects": ["Resume Parser API - FastAPI service extracting structured data from PDFs",
                     "Open-source contributor to a Python async task library"],
        "certifications": ["AWS Certified Developer - Associate"],
    },
    {
        "_file": "02_priya_nair_python_flask.docx", "_profile": "MODERATE match - related skills (Flask, MySQL)",
        "name": "Priya Nair", "email": "priya.nair@example.com", "phone": "+91 91234 56780",
        "summary": "Backend developer with around 3.5 years of experience building web applications in "
                   "Python using Flask and MySQL.",
        "experience": [
            ("Backend Developer", "Lotus Digital", "Mar 2023 - Present", [
                "Built Flask web services and RESTful APIs for an e-commerce platform",
                "Designed MySQL schemas and wrote stored procedures",
                "Used Docker for local development environments"]),
            ("Software Engineer", "Kite Softwares", "Jun 2021 - Feb 2023", [
                "Developed internal dashboards with Python and JavaScript",
                "Wrote unit tests and maintained Git workflows"]),
        ],
        "skills": "Python, Flask, MySQL, REST API, Docker, Git, JavaScript, HTML, CSS, Unit Testing",
        "education": [("B.Sc in Information Technology", "University of Mumbai", "2018 - 2021")],
        "projects": ["Inventory management system - Flask + MySQL"],
        "certifications": [],
    },
    {
        "_file": "03_rohan_verma_junior.pdf", "_profile": "WEAK/MODERATE - junior, internship only",
        "name": "Rohan Verma", "email": "rohan.verma@example.com", "phone": "+91 99887 76655",
        "summary": "Recent graduate passionate about Python and web development.",
        "experience": [
            ("Python Intern", "StartUpHub", "Jan 2025 - Dec 2025", [
                "Built CRUD pages with Django and SQLite",
                "Fixed bugs and wrote documentation"]),
        ],
        "skills": "Python, Django, SQLite, HTML, CSS, Git",
        "education": [("Bachelor of Computer Applications (BCA)", "Delhi University College of Computing", "2021 - 2024")],
        "projects": ["Blog application using Django", "Weather dashboard using a public API"],
        "certifications": ["Python for Everybody - online course"],
    },
    {
        "_file": "04_sneha_iyer_data_scientist.docx", "_profile": "STRONG match - Data Scientist",
        "name": "Sneha Iyer", "email": "sneha.iyer@example.com", "phone": "+91 90000 11122",
        "summary": "Data scientist with 5 years of experience in statistical modeling, machine learning and "
                   "data visualization for business decision making.",
        "experience": [
            ("Senior Data Scientist", "Insightly Analytics", "Apr 2023 - Present", [
                "Built churn prediction models with scikit-learn and XGBoost, improving retention by 12%",
                "Designed and analyzed A/B tests using hypothesis testing",
                "Created Tableau dashboards for leadership"]),
            ("Data Scientist", "RetailMind", "Aug 2020 - Mar 2023", [
                "Performed exploratory data analysis with pandas and NumPy on 50M+ rows",
                "Developed demand forecasting models (time series, Prophet)",
                "Wrote complex SQL queries and feature engineering pipelines"]),
        ],
        "skills": "Python, pandas, NumPy, scikit-learn, XGBoost, Statistics, SQL, Tableau, Matplotlib, "
                  "Machine Learning, Time Series, Feature Engineering, Jupyter",
        "education": [("M.Sc in Statistics", "Indian Statistical Institute", "2018 - 2020"),
                      ("B.Sc in Mathematics", "Stella Maris College", "2015 - 2018")],
        "projects": ["Customer segmentation using clustering", "Sales forecasting dashboard"],
        "certifications": ["Google Data Analytics Professional Certificate"],
    },
    {
        "_file": "05_karan_malhotra_ml_engineer.pdf", "_profile": "STRONG match - AI/ML Engineer",
        "name": "Karan Malhotra", "email": "karan.malhotra@example.com", "phone": "+91 98111 22334",
        "summary": "Machine learning engineer with 4 years of experience in deep learning, NLP and MLOps.",
        "experience": [
            ("Machine Learning Engineer", "NeuralWorks AI", "Feb 2022 - Present", [
                "Fine-tuned transformer models (BERT) with PyTorch for document classification",
                "Built semantic search using sentence embeddings and FAISS vector database",
                "Deployed models with Docker and Kubernetes; tracked experiments with MLflow"]),
            ("ML Engineer", "DataSpark", "Oct 2020 - Jan 2022", [
                "Trained TensorFlow models for NLP and computer vision tasks",
                "Implemented cross-validation and hyperparameter tuning pipelines"]),
        ],
        "skills": "Python, PyTorch, TensorFlow, Deep Learning, NLP, Transformers, Hugging Face, LLMs, "
                  "scikit-learn, Docker, Kubernetes, MLOps, AWS, SQL",
        "education": [("M.Tech in Artificial Intelligence", "Indian Institute of Technology Hyderabad", "2018 - 2020")],
        "projects": ["RAG chatbot using LangChain and a vector database", "Image classifier with CNNs"],
        "certifications": ["TensorFlow Developer Certificate"],
    },
    {
        "_file": "06_ananya_gupta_frontend.docx", "_profile": "WEAK match for Python role - frontend",
        "name": "Ananya Gupta", "email": "ananya.gupta@example.com", "phone": "+91 97777 88899",
        "summary": "Frontend engineer with 4 years of experience crafting responsive interfaces with React "
                   "and TypeScript.",
        "experience": [
            ("Frontend Engineer", "PixelCraft Studios", "May 2022 - Present", [
                "Built React and TypeScript single-page applications",
                "Implemented design systems with Tailwind CSS"]),
            ("UI Developer", "WebWeavers", "Jan 2021 - Apr 2022", [
                "Developed responsive pages with HTML, CSS and JavaScript"]),
        ],
        "skills": "JavaScript, TypeScript, React, HTML, CSS, Tailwind CSS, Git, Node.js",
        "education": [("B.E. in Electronics and Communication", "Anna University College of Engineering", "2016 - 2020")],
        "projects": ["Portfolio website builder"],
        "certifications": [],
    },
    {
        "_file": "07_vikram_singh_java.pdf", "_profile": "WEAK/MODERATE - Java backend, transferable skills",
        "name": "Vikram Singh", "email": "vikram.singh@example.com", "phone": "+91 96666 55544",
        "summary": "Backend engineer with 7 years of experience designing microservices in Java and Spring Boot.",
        "experience": [
            ("Lead Backend Engineer", "FinCore Systems", "Mar 2021 - Present", [
                "Architected Spring Boot microservices processing payments",
                "Used Kafka for event streaming and PostgreSQL for persistence",
                "Deployed services with Docker and Kubernetes on AWS"]),
            ("Java Developer", "Enterprise Soft", "Jul 2018 - Feb 2021", [
                "Built REST APIs in Java and wrote JUnit tests"]),
            ("Associate Engineer", "TechBridge", "Jun 2017 - Jun 2018", [
                "Maintained legacy Java applications"]),
        ],
        "skills": "Java, Spring Boot, Microservices, Kafka, PostgreSQL, SQL, Docker, Kubernetes, AWS, Git, REST API",
        "education": [("B.Tech in Computer Science", "Punjab Engineering College", "2013 - 2017")],
        "projects": ["Payment gateway integration"],
        "certifications": ["Oracle Certified Java Programmer"],
    },
    {
        "_file": "08_meera_krishnan_cv_phd.docx", "_profile": "AI/ML - PhD, overlapping research + industry",
        "name": "Meera Krishnan", "email": "meera.krishnan@example.com", "phone": "+91 95555 44433",
        "summary": "Computer vision researcher with a PhD and industry experience in deep learning.",
        "experience": [
            ("Computer Vision Engineer", "VisionLoop", "Jan 2024 - Present", [
                "Built object detection models with PyTorch and deployed them with ONNX"]),
            ("Research Assistant", "IISc Vision Lab", "Aug 2019 - Jun 2024", [
                "Researched deep learning methods for medical image segmentation",
                "Published 3 papers on convolutional neural networks"]),
        ],
        "skills": "Python, PyTorch, Computer Vision, Deep Learning, OpenCV, NumPy, CUDA, Machine Learning",
        "education": [("PhD in Computer Science", "Indian Institute of Science", "2019 - 2024"),
                      ("B.Tech in Computer Science", "College of Engineering Pune", "2015 - 2019")],
        "projects": ["Medical image segmentation toolkit"],
        "certifications": [],
    },
    {
        "_file": "09_arjun_rao_data_analyst.pdf", "_profile": "MODERATE for Data Scientist - analyst",
        "name": "Arjun Rao", "email": "arjun.rao@example.com", "phone": "+91 94444 33322",
        "summary": "Data analyst with 2 years of experience in SQL, Excel and Power BI reporting.",
        "experience": [
            ("Data Analyst", "MarketPulse", "Sep 2024 - Present", [
                "Built Power BI dashboards and automated Excel reports",
                "Wrote SQL queries for weekly business metrics",
                "Performed basic data analysis in Python with pandas"]),
        ],
        "skills": "SQL, Excel, Power BI, Python, pandas, Data Analysis, Data Visualization",
        "education": [("B.Com", "Osmania University", "2018 - 2021")],
        "projects": ["Sales KPI dashboard"],
        "certifications": ["Microsoft Power BI Data Analyst"],
    },
    {
        "_file": "10_fatima_sheikh_overlap.docx", "_profile": "MODERATE/STRONG - overlapping jobs (freelance)",
        "name": "Fatima Sheikh", "email": "fatima.sheikh@example.com", "phone": "+91 93333 22211",
        "summary": "Python and Django developer who also freelances on AWS projects.",
        "personal": ["Date of Birth: 12/04/1995", "Gender: Female", "Marital Status: Single"],
        "experience": [
            ("Django Developer", "AppNest", "Jan 2020 - Dec 2023", [
                "Built Django REST APIs backed by PostgreSQL",
                "Wrote pytest suites and Docker images"]),
            ("Freelance Python Developer", "Self-employed", "Jun 2021 - Jun 2023", [
                "Delivered AWS Lambda and S3 automation scripts for clients"]),
            ("Python Developer", "CodeCraft", "Feb 2024 - Present", [
                "Maintaining FastAPI services and Redis caching"]),
        ],
        "skills": "Python, Django, FastAPI, PostgreSQL, Docker, AWS, Redis, pytest, Git, REST API",
        "education": [("B.E. in Computer Engineering", "Pune Institute of Computer Technology", "2015 - 2019")],
        "projects": ["Multi-tenant SaaS billing module"],
        "certifications": [],
    },
    {
        "_file": "11_daniel_thomas_career_change.pdf", "_profile": "WEAK - career changer, diploma",
        "name": "Daniel Thomas", "email": "daniel.thomas@example.com", "phone": "+91 92222 11100",
        "summary": "Mechanical engineer transitioning into software, completed a Python bootcamp.",
        "experience": [
            ("Mechanical Design Engineer", "AutoParts Manufacturing", "Jun 2019 - May 2024", [
                "Designed automotive components using CAD tools",
                "Automated test reports with Excel macros"]),
        ],
        "skills": "Python, Excel, Data Analysis, Git",
        "education": [("Diploma in Mechanical Engineering", "Government Polytechnic Kochi", "2016 - 2019")],
        "projects": ["Python bootcamp capstone: expense tracker"],
        "certifications": ["Full-stack Python bootcamp"],
    },
    {
        "_file": "12_neha_joshi_nlp_synonyms.docx", "_profile": "AI/ML - semantically related skills & synonyms",
        "name": "Neha Joshi", "email": "neha.joshi@example.com", "phone": "+91 91111 00099",
        "summary": "NLP engineer with 3 years of hands-on experience building language applications with "
                   "Hugging Face, BERT and Keras.",
        "experience": [
            ("NLP Engineer", "LinguaTech", "Nov 2023 - Present", [
                "Built retrieval augmented generation (RAG) assistants using LangChain and Pinecone",
                "Fine-tuned BERT models with Hugging Face for named entity recognition"]),
            ("Junior Data Scientist", "TextIQ", "Oct 2022 - Oct 2023", [
                "Trained Keras neural networks for text classification",
                "Packaged models as containers for deployment"]),
        ],
        "skills": "Python, Hugging Face, BERT, Keras, Neural Networks, Natural Language Processing, "
                  "LangChain, Pinecone, Containerization, scikit-learn",
        "education": [("M.S. in Computer Science", "University of Hyderabad", "2020 - 2022")],
        "projects": ["Legal document question answering system"],
        "certifications": ["DeepLearning.AI NLP Specialization"],
    },
]
