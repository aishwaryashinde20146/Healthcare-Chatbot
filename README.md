# Healthcare AI Chatbot & Medical Image Analysis

A comprehensive Flask-based healthcare platform that combines AI-powered symptom analysis with medical image analysis capabilities. The application supports both text and voice inputs for symptom consultation and includes advanced medical image analysis using Google's Gemini AI.

## 🚀 **Key Features**

### **AI-Powered Symptom Analysis**
- Text-based symptom input with intelligent analysis
- Voice-based symptom input with speech recognition
- Real-time symptom analysis using Google Gemini 2.0 Flash
- Intelligent severity assessment (Low/Medium/High urgency)
- Smart doctor recommendation system

### **Medical Image Analysis** ⭐ *NEW*
- Upload and analyze medical images (X-rays, scans, etc.)
- AI-powered image interpretation using Google Gemini Vision
- Detailed analysis reports with findings and recommendations
- Drag-and-drop image upload interface
- Instant visual feedback and results

### **Advanced Features**
- Integrated appointment booking system
- Professional PDF report generation
- Medical advice documentation
- Appointment confirmation PDFs
- 24/7 availability with real-time processing

### **Modern User Interface**
- Responsive, mobile-first design
- Healthcare-themed professional interface
- Real-time chat functionality
- Voice recording with visual feedback
- Image upload with preview and analysis

## 📋 **Prerequisites**

- Python 3.8 or higher
- Google Gemini API key
- Microphone access (for voice input)
- Modern web browser with JavaScript enabled

## 🛠️ **Installation & Setup**

1. **Clone the repository:**
```bash
git clone <repository-url>
cd healthcare-chatbot
```

2. **Install required packages:**
```bash
pip install -r requirements.txt
```

3. **Configure API keys in `config.py`:**
```python
GEMINI_API_KEY = 'your_gemini_api_key_here'
```

4. **Run the application:**
```bash
python app.py
```

5. **Access the application:**
```
http://localhost:5000
```

## 📱 **Usage Guide**

### **Symptom Analysis**
1. **Text Input**: Type your symptoms in the chat interface
2. **Voice Input**: Click the microphone button and speak your symptoms
3. **Get Analysis**: Receive detailed medical analysis with recommendations

### **Medical Image Analysis** 
1. **Upload Image**: Drag and drop or click to upload medical images
2. **AI Analysis**: Get instant AI-powered analysis of your medical images
3. **Detailed Reports**: Receive comprehensive findings and recommendations
4. **Download PDFs**: Save professional medical reports

### **Appointment Booking**
1. **Book Appointment**: Click "Book Appointment" from analysis results
2. **Fill Details**: Complete the appointment booking form
3. **Confirmation**: Receive appointment confirmation with PDF

## 🔧 **Technical Architecture**

### **Backend Technologies**
- **Flask 3.0.2**: Web framework
- **Google Generative AI**: Gemini 2.0 Flash for text and vision analysis
- **SpeechRecognition**: Voice input processing
- **ReportLab**: Professional PDF generation
- **PyDub**: Audio processing and enhancement

### **Frontend Technologies**
- **HTML5/CSS3**: Modern web standards
- **Tailwind CSS**: Utility-first CSS framework
- **JavaScript (ES6+)**: Interactive functionality
- **Font Awesome**: Professional icons
- **Responsive Design**: Mobile-optimized interface

### **API Endpoints**
- `/` - Main application interface
- `/process_text` - Text symptom analysis
- `/process_voice` - Voice input processing
- `/analyze_image` - Medical image analysis ⭐ *NEW*
- `/book_appointment` - Appointment booking
- `/generate_medical_pdf` - Medical report generation
- `/generate_appointment_pdf` - Appointment confirmation PDFs

## 📊 **Response Format**

The application provides comprehensive analysis including:

1. **Symptom Analysis**: Detailed breakdown of reported symptoms
2. **Possible Conditions**: AI-identified potential medical conditions
3. **Severity Assessment**: Urgency level classification
4. **Immediate Recommendations**: Actionable advice and next steps
5. **Doctor Consultation**: Intelligent recommendation for medical consultation
6. **Professional Documentation**: Downloadable PDF reports

## 🔒 **Security & Privacy**

- **No Data Storage**: Session-based processing only
- **API Security**: Secure API key management
- **Input Validation**: Protected against malicious inputs
- **Medical Disclaimers**: Clear liability limitations
- **Privacy First**: Minimal data collection approach

## ⚠️ **Important Medical Disclaimer**

This application is designed for informational purposes only and should not be used as a substitute for professional medical advice, diagnosis, or treatment. Always consult with qualified healthcare providers for proper medical care. In case of medical emergencies, contact emergency services immediately.

## 🚀 **Future Enhancements**

- **Multi-language Support**: International accessibility
- **EHR Integration**: Electronic health record connectivity
- **Mobile App**: Native iOS/Android applications
- **Advanced Analytics**: Health tracking and trends
- **Telemedicine Integration**: Video consultation capabilities

## 📝 **Dependencies**

```
flask==3.0.2
google-generativeai==0.3.2
python-dotenv==1.0.1
SpeechRecognition==3.10.1
pydub==0.25.1
reportlab==4.0.7
```

## 📄 **License**

MIT License - See LICENSE file for details

---

**Version**: 2.0.0  
**Last Updated**: December 2024  
**Compatibility**: Python 3.8+, Modern Browsers 