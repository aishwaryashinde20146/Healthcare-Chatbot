from flask import Flask, render_template, request, jsonify, send_file
import google.generativeai as genai
import speech_recognition as sr
from pydub import AudioSegment
import os
import tempfile
from config import GEMINI_API_KEY
from datetime import datetime
import json

# PDF generation imports
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from io import BytesIO

app = Flask(__name__)

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# Store session data (in production, use a proper database)
session_data = {}

def process_symptoms(symptoms):
    try:
        # Enhanced medical analysis prompt for balanced and realistic assessments
        prompt = f"""
        You are an expert medical AI assistant providing balanced healthcare guidance. A patient has described their symptoms: "{symptoms}"
        
        Please provide a realistic medical analysis using clinical judgment. Be balanced - not everything requires immediate medical attention.

        **Symptom Analysis:**
        Analyze the described symptoms objectively. Consider if these are common, mild conditions that may resolve on their own versus more serious concerns.

        **Potential Conditions:**
        List 2-3 possible conditions, starting with the most likely (often the simplest explanation). Include both common benign conditions and any serious conditions if warranted.

        **Severity Assessment:**
        Realistically assess severity, especially for common conditions:
        - Mild: Common cold symptoms (runny nose, mild cough, sneezing), minor headaches, slight fatigue, muscle soreness from activity, minor aches
        - Moderate: Symptoms lasting more than 3-5 days, moderate pain, persistent cough with fever, recurring issues
        - Severe: Symptoms requiring prompt medical care (chest pain, breathing difficulties, severe injuries, high fever 104°F+)
        
        **Important**: Common conditions like colds, minor headaches, slight fatigue should typically be classified as MILD unless there are concerning complications.

        **Doctor Consultation:**
        Provide balanced medical guidance:
        - URGENT: Life-threatening symptoms, severe pain, breathing difficulties, chest pain, signs of stroke, severe injuries, high fever (104°F+)
        - RECOMMENDED: Moderate symptoms, persistent issues lasting 3+ days, concerning changes, fever 101-103°F, moderate pain
        - ADVISABLE: Mild-moderate symptoms that don't improve with self-care, recurring issues, symptoms affecting daily activities
        - OPTIONAL: Very mild symptoms (minor occasional headache, slight tiredness after exertion, minor muscle soreness from activity)
        
        **For Common Conditions**: Regular colds, minor headaches, slight fatigue, and similar common symptoms should typically be classified as OPTIONAL unless they are severe, persistent (5+ days), or accompanied by concerning symptoms.

        **Immediate Recommendations:**
        Focus on practical self-care for mild symptoms:
        - Home remedies and over-the-counter treatments for common issues
        - When to escalate to medical care
        - Lifestyle modifications

        **Follow-up Care:**
        Provide balanced monitoring advice - not everything needs medical follow-up.

        Remember: Most minor symptoms (headaches, slight fatigue, minor muscle pain, etc.) are common and don't require immediate medical attention. Reserve urgent classifications for truly serious symptoms.
        """
        
        response = model.generate_content(prompt)
        
        if response and response.text:
            analysis_text = response.text.strip()
            
            # Parse doctor recommendation and urgency
            doctor_needed = extract_doctor_recommendation(analysis_text)
            urgency_level = extract_urgency_level(analysis_text)
            
            print(f"Analysis generated: doctor_needed={doctor_needed}, urgency={urgency_level}")
            
            return {
                "analysis": analysis_text,
                "doctor_needed": doctor_needed,
                "urgency_level": urgency_level,
                "symptoms": symptoms,
                "success": True
            }
        else:
            return {
                "error": "Failed to generate medical analysis",
                "success": False
            }
    except Exception as e:
        print(f"Error in process_symptoms: {str(e)}")
        return {
            "error": f"API Error: {str(e)}",
            "success": False
        }

def extract_doctor_recommendation(text):
    """Extract whether doctor visit is recommended from the response"""
    text_lower = text.lower()
    
    # Check for explicit urgent medical needs first
    urgent_patterns = ['urgent:', 'seek immediate medical attention', 'emergency', 'call emergency', 'go to emergency', 'life-threatening', 'severe pain', 'breathing difficulties', 'chest pain']
    if any(pattern in text_lower for pattern in urgent_patterns):
        return True
    
    # Check for clear medical consultation recommendations
    recommended_patterns = ['recommended:', 'schedule appointment', 'see a doctor', 'consult a healthcare', 'medical attention', 'physician', 'healthcare provider']
    if any(pattern in text_lower for pattern in recommended_patterns):
        return True
    
    # Check for advisory medical consultation
    advisable_patterns = ['advisable:', 'consider consulting', 'consider seeing', 'if symptoms persist', 'don\'t improve', 'getting worse', 'not better', 'worsening']
    if any(pattern in text_lower for pattern in advisable_patterns):
        return True
    
    # Check for concerning symptoms that warrant medical attention
    concerning_patterns = ['persistent', 'chronic', 'recurring', 'lasted more than', 'ongoing for', 'concerning', 'unusual', 'moderate pain', 'fever over']
    if any(pattern in text_lower for pattern in concerning_patterns):
        return True
    
    # Check for optional/self-care patterns (these suggest doctor visit is NOT needed)
    optional_patterns = ['optional:', 'monitor symptoms', 'home care sufficient', 'self-care', 'typically resolve on their own', 'usually harmless', 'simple rest', 'over-the-counter sufficient']
    if any(pattern in text_lower for pattern in optional_patterns):
        return False
    
    # Check for very mild indicators
    very_mild_patterns = ['very mild', 'minor headache', 'slight fatigue', 'minor aches', 'very common', 'nothing to worry']
    if any(pattern in text_lower for pattern in very_mild_patterns):
        return False
    
    # Context-based decision for common conditions
    common_conditions = ['cold', 'common cold', 'runny nose', 'stuffy nose', 'sneezing', 'cough', 'sore throat', 'headache', 'fatigue', 'tired', 'ache', 'sore', 'muscle pain', 'congestion']
    if any(condition in text_lower for condition in common_conditions):
        # For common conditions, only recommend doctor if severe or persistent
        if any(modifier in text_lower for modifier in ['severe', 'intense', 'constant', 'worsening', 'unbearable', 'high fever', 'difficulty breathing', 'persistent', 'lasting over', 'ongoing for', 'not improving', 'getting worse']):
            return True
        # For mild/normal common conditions, don't recommend doctor
        else:
            return False
    
    # Default to recommending doctor visit for unclear cases (changed back to True for safety)
    return True

def extract_urgency_level(text):
    """Extract urgency level from the response with balanced assessment"""
    text_lower = text.lower()
    
    # Check for high urgency indicators first (most critical)
    high_urgency = ['urgent:', 'severe', 'emergency', 'immediate', 'life-threatening', 'breathing difficulties', 'chest pain', 'severe pain', 'stroke', 'severe injuries', 'high fever', 'severe bleeding', 'severe allergic reaction']
    if any(indicator in text_lower for indicator in high_urgency):
        return 'High'
    
    # Check for medium urgency (needs medical attention but not urgent)
    medium_urgency = ['recommended:', 'moderate', 'medium severity', 'persistent symptoms', 'concerning changes', 'fever over', 'worsening', 'recurring', 'chronic', 'ongoing for', 'lasted more than', 'getting worse', 'not improving']
    if any(indicator in text_lower for indicator in medium_urgency):
        return 'Medium'
    
    # Check for specifically low urgency indicators
    low_urgency = ['optional:', 'mild', 'low severity', 'minor headache', 'slight fatigue', 'minor aches', 'very common', 'typically resolve quickly', 'simple rest', 'usually harmless']
    if any(indicator in text_lower for indicator in low_urgency):
        return 'Low'
    
    # Check for advisable (medium priority)
    if 'advisable:' in text_lower or 'if symptoms persist' in text_lower:
        return 'Medium'
    
    # Check for common mild conditions first (should be LOW priority)
    common_mild_conditions = ['cold', 'common cold', 'runny nose', 'stuffy nose', 'sneezing', 'cough', 'sore throat', 'headache', 'fatigue', 'tired', 'ache', 'sore', 'muscle pain', 'congestion', 'nasal congestion']
    if any(condition in text_lower for condition in common_mild_conditions):
        # Check if there are severe modifiers that would increase priority
        if any(modifier in text_lower for modifier in ['severe', 'intense', 'extreme', 'unbearable', 'constant', 'high fever', 'difficulty breathing', 'chest pain', 'worsening rapidly']):
            return 'Medium'  # Even severe common conditions are usually Medium, not High
        elif any(modifier in text_lower for modifier in ['persistent', 'lasting', 'ongoing', 'not improving', 'getting worse', 'chronic']):
            return 'Medium'  # Persistent common symptoms warrant medical attention
        else:
            return 'Low'  # Default for common conditions without severe modifiers
    
    # Default to Medium for balanced assessment
    return 'Medium'

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/process_text', methods=['POST'])
def process_text():
    try:
        data = request.get_json()
        symptoms = data.get('symptoms', '')
        
        if not symptoms:
            return jsonify({"error": "No symptoms provided"}), 400
        
        response = process_symptoms(symptoms)
        
        if response.get('success'):
            return jsonify(response)
        else:
            return jsonify({"error": response.get('error', 'Unknown error')}), 500
            
    except Exception as e:
        print(f"Error in process_text: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/process_voice', methods=['POST'])
def process_voice():
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files['audio']
        print(f"Received audio file: {audio_file.filename}, Content-Type: {audio_file.content_type}")
        
        # Read the audio file content
        audio_data = audio_file.read()
        print(f"Audio file size: {len(audio_data)} bytes")
        
        if len(audio_data) == 0:
            return jsonify({"error": "Empty audio file received"}), 400
        
        # Save the audio file temporarily
        temp_file_extension = '.webm'  # Default to webm since most browsers use this
        if audio_file.content_type:
            if 'webm' in audio_file.content_type:
                temp_file_extension = '.webm'
            elif 'mp4' in audio_file.content_type:
                temp_file_extension = '.mp4'
            elif 'wav' in audio_file.content_type:
                temp_file_extension = '.wav'
            elif 'ogg' in audio_file.content_type:
                temp_file_extension = '.ogg'
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=temp_file_extension) as temp_audio:
            temp_audio.write(audio_data)
            temp_audio_path = temp_audio.name
        
        print(f"Saved audio to: {temp_audio_path}")
        
        try:
            # Convert audio to text with optimized settings
            recognizer = sr.Recognizer()
            recognizer.energy_threshold = 200  # Lower threshold for better sensitivity
            recognizer.dynamic_energy_threshold = True
            recognizer.pause_threshold = 0.8
            recognizer.phrase_threshold = 0.3
            
            # Try to process different audio formats
            audio_processed = False
            symptoms = ""
            
            # Method 1: Try direct processing if it's WAV
            if temp_file_extension == '.wav':
                try:
                    with sr.AudioFile(temp_audio_path) as source:
                        print(f"Processing WAV file directly")
                        recognizer.adjust_for_ambient_noise(source, duration=0.2)
                        audio_data_sr = recognizer.record(source)
                        symptoms = recognizer.recognize_google(audio_data_sr, language='en-US')
                        audio_processed = True
                        print(f"WAV processing successful: {symptoms}")
                except Exception as wav_error:
                    print(f"WAV processing failed: {wav_error}")
            
            # Method 2: Try using pydub to convert to WAV first
            if not audio_processed:
                try:
                    from pydub import AudioSegment
                    
                    # Load audio with pydub - try multiple formats
                    audio_segment = None
                    try:
                        if temp_file_extension == '.webm':
                            audio_segment = AudioSegment.from_file(temp_audio_path, format="webm")
                        elif temp_file_extension == '.mp4':
                            audio_segment = AudioSegment.from_file(temp_audio_path, format="mp4")
                        elif temp_file_extension == '.ogg':
                            audio_segment = AudioSegment.from_file(temp_audio_path, format="ogg")
                        else:
                            # Try auto-detect format
                            audio_segment = AudioSegment.from_file(temp_audio_path)
                    except Exception as format_error:
                        print(f"Format-specific loading failed: {format_error}")
                        # Try loading without specifying format
                        try:
                            audio_segment = AudioSegment.from_file(temp_audio_path)
                        except Exception as generic_error:
                            print(f"Generic loading failed: {generic_error}")
                            # Try loading as raw audio
                            audio_segment = AudioSegment.from_file(temp_audio_path, format="raw", 
                                                                frame_rate=16000, channels=1, sample_width=2)
                    
                    if audio_segment is None:
                        raise Exception("Could not load audio file in any format")
                    
                    print(f"Audio segment loaded: duration={len(audio_segment)}ms, channels={audio_segment.channels}, frame_rate={audio_segment.frame_rate}")
                    
                    # Ensure audio is in a good format for speech recognition
                    # Convert to mono if stereo
                    if audio_segment.channels > 1:
                        audio_segment = audio_segment.set_channels(1)
                    
                    # Set sample rate to 16kHz for better speech recognition
                    if audio_segment.frame_rate != 16000:
                        audio_segment = audio_segment.set_frame_rate(16000)
                    
                    # Normalize audio volume
                    audio_segment = audio_segment.normalize()
                    
                    # Convert to WAV format
                    wav_path = temp_audio_path.replace(temp_file_extension, '_converted.wav')
                    audio_segment.export(wav_path, format="wav")
                    print(f"Converted audio saved to: {wav_path}")
                    
                    # Now process with speech recognition
                    with sr.AudioFile(wav_path) as source:
                        recognizer.adjust_for_ambient_noise(source, duration=0.3)
                        audio_data_sr = recognizer.record(source)
                        
                        # Try Google Speech Recognition first
                        try:
                            symptoms = recognizer.recognize_google(audio_data_sr, language='en-US')
                            audio_processed = True
                            print(f"Google Speech Recognition successful: {symptoms}")
                        except sr.UnknownValueError:
                            print("Google Speech Recognition could not understand audio")
                            # Try with different language settings
                            try:
                                symptoms = recognizer.recognize_google(audio_data_sr, language='en')
                                audio_processed = True
                                print(f"Google Speech Recognition (en) successful: {symptoms}")
                            except:
                                print("All Google Speech Recognition attempts failed")
                        except sr.RequestError as e:
                            print(f"Google Speech Recognition request error: {e}")
                    
                    # Clean up converted file
                    if os.path.exists(wav_path):
                        os.unlink(wav_path)
                    
                except Exception as convert_error:
                    print(f"Audio conversion failed: {convert_error}")
                    # Provide more specific error messages
                    error_msg = str(convert_error).lower()
                    if "ffmpeg" in error_msg or "ffprobe" in error_msg:
                        return jsonify({"error": "Audio processing requires FFmpeg. Please ensure FFmpeg is properly installed."}), 500
                    elif "codec" in error_msg:
                        return jsonify({"error": "Unsupported audio codec. Please try recording in a different format."}), 500
                    else:
                        return jsonify({"error": f"Audio conversion failed: {str(convert_error)[:100]}"}), 500
            
            # Clean up original file
            if os.path.exists(temp_audio_path):
                os.unlink(temp_audio_path)
            
            if not audio_processed:
                return jsonify({"error": "Could not process audio. Please ensure you have a working microphone and speak clearly, or try using text input instead."}), 400
            
            if not symptoms.strip():
                return jsonify({"error": "No speech detected in the audio. Please speak more clearly and ensure your microphone is working properly."}), 400
            
            print(f"Final transcription: {symptoms}")
            
            # Process the symptoms
            response = process_symptoms(symptoms)
            if response.get('success'):
                response['transcribed_text'] = symptoms
                return jsonify(response)
            else:
                return jsonify({"error": response.get('error', 'Unknown error')}), 500
                
        except sr.UnknownValueError:
            return jsonify({"error": "Could not understand the audio. Please speak clearly and try again."}), 400
        except sr.RequestError as e:
            return jsonify({"error": f"Speech recognition service error: {str(e)}. Please check your internet connection."}), 500
        except Exception as processing_error:
            print(f"Audio processing error: {str(processing_error)}")
            return jsonify({"error": f"Audio processing failed: {str(processing_error)[:100]}"}), 500
                    
    except Exception as e:
        print(f"Error in process_voice: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)[:100]}"}), 500

@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    try:
        data = request.get_json()
        patient_name = data.get('patient_name', '')
        phone = data.get('phone', '')
        email = data.get('email', '')
        date = data.get('date', '')
        time = data.get('time', '')
        urgency = data.get('urgency', 'Medium')
        notes = data.get('notes', '')
        symptoms = data.get('symptoms', '')
        analysis_summary = data.get('analysis_summary', '')
        
        # Validate required fields
        if not all([patient_name, phone, date, time]):
            return jsonify({"error": "Please fill in all required fields"}), 400
        
        # Validate phone number format
        import re
        phone_clean = re.sub(r'[\s\-\(\)]', '', phone)
        if not re.match(r'^[\+]?[1-9][\d]{0,15}$', phone_clean):
            return jsonify({"error": "Invalid phone number format"}), 400
        
        # Generate unique appointment ID
        import uuid
        appointment_id = f"APT{uuid.uuid4().hex[:8].upper()}"
        
        # Get current timestamp
        booking_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create booking confirmation data
        booking_confirmation = {
            "appointment_id": appointment_id,
            "patient_name": patient_name,
            "phone": phone,
            "email": email,
            "date": date,
            "time": time,
            "urgency": urgency,
            "notes": notes,
            "symptoms": symptoms,
            "analysis_summary": analysis_summary,
            "status": "Confirmed",
            "booking_time": booking_time,
            "clinic_info": {
                "name": "HealthCare AI Clinic",
                "address": "123 Medical Center Drive, Healthcare City",
                "phone": "+1 (555) 123-CARE",
                "email": "appointments@healthcareai.com"
            }
        }
        
        print(f"Appointment booked: {appointment_id} for {patient_name} on {date} at {time}")
        
        return jsonify({
            "success": True,
            "appointment_id": appointment_id,
            "booking": booking_confirmation,
            "message": f"Appointment booked successfully! ID: {appointment_id}"
        })
        
    except Exception as e:
        print(f"Error in book_appointment: {str(e)}")
        return jsonify({"error": f"Booking error: {str(e)}"}), 500

@app.route('/generate_medical_pdf', methods=['POST'])
def generate_medical_pdf():
    try:
        data = request.get_json()
        symptoms = data.get('symptoms', '')
        analysis = data.get('analysis', '')
        urgency = data.get('urgency', 'Medium')
        doctor_needed = data.get('doctor_needed', False)
        
        if not symptoms or not analysis:
            return jsonify({"error": "Missing symptoms or analysis data"}), 400
        
        # Generate enhanced medical report PDF
        pdf_buffer = generate_medical_report_pdf(symptoms, analysis, urgency, doctor_needed)
        
        filename = f"medical_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return send_file(
            BytesIO(pdf_buffer),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Error in generate_medical_pdf: {str(e)}")
        return jsonify({"error": f"PDF generation error: {str(e)}"}), 500

@app.route('/analyze_image', methods=['POST'])
def analyze_image():
    try:
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
        
        image_file = request.files['image']
        print(f"Received image file: {image_file.filename}, Content-Type: {image_file.content_type}")
        
        # Read the image file content
        image_data = image_file.read()
        print(f"Image file size: {len(image_data)} bytes")
        
        if len(image_data) == 0:
            return jsonify({"error": "Empty image file received"}), 400
        
        # Validate file type
        if not image_file.content_type or not image_file.content_type.startswith('image/'):
            return jsonify({"error": "Invalid file type. Please upload an image file."}), 400
        
        # Save the image file temporarily
        import base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        try:
            # Prepare the image for Gemini API
            import google.generativeai as genai
            
            # Create the image part for Gemini
            image_part = {
                "mime_type": image_file.content_type,
                "data": image_base64
            }
            
            # Balanced medical image analysis prompt
            analysis_prompt = """
            You are an expert medical AI assistant providing balanced image analysis. Please be realistic and avoid over-interpreting normal variations.

            **Image Assessment**: First determine if this is actually a medical image showing health concerns. If it's a regular photo, screenshot, or non-medical image, clearly state this is not a medical concern.

            **Visual Analysis**: If medical-related, describe only what is clearly abnormal or concerning. Many minor variations, small marks, or common skin issues are normal and don't require medical attention.

            **Realistic Evaluation**:
            - MILD/LOW PRIORITY: Most minor skin variations, small marks, common issues that typically resolve on their own
            - MODERATE: Persistent, unusual changes, or concerning symptoms that warrant routine medical consultation 
            - SEVERE/HIGH PRIORITY: Only for obviously serious conditions - severe injuries, signs of serious infections, clear medical emergencies

            **Balanced Recommendations**:
            - For minor issues: Focus on self-care, monitoring, over-the-counter treatments
            - Reserve urgent medical recommendations only for clearly serious conditions
            - Most skin marks, small variations, or minor issues don't need immediate medical attention

            **Important Guidelines**:
            - Don't over-interpret normal variations or minor marks
            - Most people have minor skin variations that are completely normal
            - Reserve "urgent" classifications only for obviously serious conditions
            - If unclear or minor issue, suggest monitoring rather than immediate medical care

            Remember: Not everything visible needs medical attention. Be balanced and realistic in your assessment.
            """
            
            # Generate analysis using Gemini
            response = model.generate_content([analysis_prompt, image_part])
            
            if not response or not response.text:
                return jsonify({"error": "Failed to analyze image. Please try again."}), 500
            
            analysis_text = response.text.strip()
            print(f"Image analysis generated: {len(analysis_text)} characters")
            
            # Extract urgency level from the analysis
            urgency_level = extract_urgency_level(analysis_text)
            
            # Extract recommendations
            recommendations = extract_recommendations(analysis_text)
            
            return jsonify({
                "success": True,
                "analysis": analysis_text,
                "recommendations": recommendations,
                "urgency_level": urgency_level,
                "message": "Image analysis completed successfully"
            })
            
        except Exception as analysis_error:
            print(f"Image analysis error: {str(analysis_error)}")
            return jsonify({"error": f"Image analysis failed: {str(analysis_error)[:100]}"}), 500
                    
    except Exception as e:
        print(f"Error in analyze_image: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)[:100]}"}), 500

def extract_recommendations(text):
    """Extract recommendations from the analysis text."""
    try:
        # Look for sections that contain recommendations
        lines = text.split('\n')
        recommendations = []
        
        in_recommendations = False
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in ['recommend', 'action', 'should', 'consider', 'advice']):
                in_recommendations = True
                if line and not line.startswith('#') and not line.startswith('*'):
                    recommendations.append(line)
            elif in_recommendations and line.startswith('-'):
                recommendations.append(line)
            elif in_recommendations and not line:
                break
        
        if recommendations:
            return ' '.join(recommendations[:3])  # Return first 3 recommendations
        
        # Fallback: return a generic recommendation
        if 'urgent' in text.lower() or 'immediate' in text.lower():
            return "Seek immediate medical attention. Contact a healthcare provider right away."
        elif 'doctor' in text.lower() or 'physician' in text.lower():
            return "Consult with a healthcare provider for proper evaluation and treatment."
        else:
            return "Monitor the condition and consider consulting a healthcare provider if symptoms persist or worsen."
            
    except Exception as e:
        print(f"Error extracting recommendations: {e}")
        return "Consult with a healthcare provider for proper evaluation and treatment."

@app.route('/generate_appointment_pdf', methods=['POST'])
def generate_appointment_pdf():
    try:
        data = request.get_json()
        booking_details = data.get('booking', {})
        
        if not booking_details:
            return jsonify({"error": "Missing booking details"}), 400
        
        # Generate appointment PDF
        pdf_buffer = generate_appointment_pdf_content(booking_details)
        
        filename = f"appointment_{booking_details.get('appointment_id', 'booking')}.pdf"
        
        return send_file(
            BytesIO(pdf_buffer),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Error in generate_appointment_pdf: {str(e)}")
        return jsonify({"error": f"PDF generation error: {str(e)}"}), 500

def generate_medical_report_pdf(symptoms, analysis, urgency, doctor_needed):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.darkblue,
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.darkred,
        spaceBefore=20,
        spaceAfter=12
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_JUSTIFY,
        spaceAfter=12
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.white,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_LEFT,
        spaceAfter=6
    )
    
    # Build PDF content
    story = []
    
    # Header with report info table
    story.append(Paragraph("🏥 AI Healthcare Assistant", title_style))
    story.append(Paragraph("Comprehensive Medical Analysis Report", styles['Heading2']))
    story.append(Spacer(1, 20))
    
    # Report information table
    current_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    report_id = f"RPT{hash(symptoms + current_time) % 10000:04d}"
    
    report_info_data = [
        [Paragraph("📋 <b>Report Information</b>", table_header_style), ""],
        ["Report ID:", report_id],
        ["Generated Date:", current_time],
        ["Report Type:", "AI Medical Analysis"],
        ["Priority Level:", f"{urgency.upper()}"],
        ["Doctor Consultation:", "RECOMMENDED" if doctor_needed else "OPTIONAL"]
    ]
    
    report_info_table = Table(report_info_data, colWidths=[2.5*inch, 3.5*inch])
    report_info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
        ('SPAN', (0, 0), (1, 0)),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    
    story.append(report_info_table)
    story.append(Spacer(1, 25))
    
    # Patient symptoms table
    story.append(Paragraph("📝 PATIENT SYMPTOMS & COMPLAINTS", header_style))
    
    symptoms_data = [
        [Paragraph("🩺 <b>Chief Complaint Details</b>", table_header_style)],
        [Paragraph(symptoms, table_cell_style)]
    ]
    
    symptoms_table = Table(symptoms_data, colWidths=[6*inch])
    symptoms_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 1), (0, 1), colors.lightyellow),
        ('TOPPADDING', (0, 1), (0, 1), 15),
        ('BOTTOMPADDING', (0, 1), (0, 1), 15)
    ]))
    
    story.append(symptoms_table)
    story.append(Spacer(1, 25))
    
    # Priority and recommendation status table
    priority_color = colors.red if urgency.lower() == 'high' else colors.orange if urgency.lower() == 'medium' else colors.green
    doctor_color = colors.red if doctor_needed else colors.green
    
    status_data = [
        [Paragraph("⚠️ <b>Priority Assessment</b>", table_header_style), Paragraph("👨‍⚕️ <b>Medical Consultation</b>", table_header_style)],
        [
            Paragraph(f"<b>{urgency.upper()} PRIORITY</b>", 
                     ParagraphStyle('Priority', parent=table_cell_style, textColor=priority_color, alignment=TA_CENTER, fontSize=14, fontName='Helvetica-Bold')),
            Paragraph(f"<b>{'RECOMMENDED' if doctor_needed else 'OPTIONAL'}</b>", 
                     ParagraphStyle('Doctor', parent=table_cell_style, textColor=doctor_color, alignment=TA_CENTER, fontSize=14, fontName='Helvetica-Bold'))
        ]
    ]
    
    status_table = Table(status_data, colWidths=[3*inch, 3*inch])
    status_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.navy),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 1), (0, 1), colors.lightgrey),
        ('BACKGROUND', (1, 1), (1, 1), colors.lightgrey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white])
    ]))
    
    story.append(status_table)
    story.append(Spacer(1, 25))
    
    # Detailed analysis sections table
    story.append(Paragraph("🔍 DETAILED MEDICAL ANALYSIS", header_style))
    
    sections = parse_analysis_sections(analysis)
    
    for section_title, section_content in sections.items():
        if section_content:
            # Create table for each analysis section
            section_icon = {
                'Symptom Analysis': '🩺',
                'Potential Conditions': '🔬',
                'Severity Assessment': '📊',
                'Doctor Consultation': '👨‍⚕️',
                'Immediate Recommendations': '⚡',
                'Follow-up Care': '📅'
            }.get(section_title, '📋')
            
            section_data = [
                [Paragraph(f"{section_icon} <b>{section_title.upper()}</b>", table_header_style)],
                [Paragraph(format_analysis_content(section_content), table_cell_style)]
            ]
            
            section_table = Table(section_data, colWidths=[6*inch])
            section_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BACKGROUND', (0, 1), (0, 1), colors.lightyellow),
                ('TOPPADDING', (0, 1), (0, 1), 12),
                ('BOTTOMPADDING', (0, 1), (0, 1), 12)
            ]))
            
            story.append(section_table)
            story.append(Spacer(1, 15))
    
    # Next steps recommendations table
    story.append(Paragraph("📋 RECOMMENDED NEXT STEPS", header_style))
    
    next_steps = []
    if doctor_needed:
        if urgency.lower() == 'high':
            next_steps = [
                "🚨 Seek IMMEDIATE medical attention",
                "📞 Contact emergency services if symptoms worsen",
                "🏥 Consider visiting emergency room if urgent",
                "📄 Bring this report to your appointment",
                "⏰ Do not delay medical consultation"
            ]
        else:
            next_steps = [
                "📞 Schedule appointment within 24-48 hours",
                "🏥 Visit your primary care physician",
                "📄 Bring this report for reference",
                "📝 Monitor symptoms closely",
                "☎️ Call if symptoms worsen"
            ]
    else:
        next_steps = [
            "🏠 Continue with home care and monitoring",
            "📊 Track symptoms for any changes",
            "📞 Contact doctor if symptoms persist",
            "💊 Follow any prescribed treatments",
            "⚕️ Schedule routine follow-up if needed"
        ]
    
    steps_data = [
        [Paragraph("📋 <b>Action Items</b>", table_header_style)],
    ]
    
    for step in next_steps:
        steps_data.append([Paragraph(step, table_cell_style)])
    
    steps_table = Table(steps_data, colWidths=[6*inch])
    steps_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ('LEFTPADDING', (0, 1), (-1, -1), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8)
    ]))
    
    story.append(steps_table)
    story.append(Spacer(1, 25))
    
    # Emergency contact information table
    story.append(Paragraph("🚨 EMERGENCY CONTACT INFORMATION", header_style))
    
    emergency_data = [
        [Paragraph("🚨 <b>Emergency Contacts</b>", table_header_style), Paragraph("📞 <b>Contact Numbers</b>", table_header_style)],
        ["Emergency Services", "911"],
        ["Poison Control", "1-800-222-1222"],
        ["Healthcare AI Clinic", "+1 (555) 123-CARE"],
        ["Urgent Care Hotline", "+1 (555) 911-HELP"],
        ["Telehealth Support", "+1 (555) 247-CHAT"]
    ]
    
    emergency_table = Table(emergency_data, colWidths=[3*inch, 3*inch])
    emergency_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.red),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    
    story.append(emergency_table)
    story.append(Spacer(1, 30))
    
    # Medical disclaimer table
    disclaimer_data = [
        [Paragraph("⚠️ <b>IMPORTANT MEDICAL DISCLAIMER</b>", table_header_style)],
        [Paragraph(
            "<b>This report is generated by an AI system and is for informational purposes only.</b><br/><br/>"
            "• This analysis should NOT replace professional medical advice, diagnosis, or treatment<br/>"
            "• The AI assessment is based on symptoms described and may not account for all medical factors<br/>"
            "• Always seek advice from qualified healthcare providers for medical conditions<br/>"
            "• In case of emergency, call your local emergency services immediately<br/>"
            "• This report is not a substitute for clinical examination by a healthcare professional",
            table_cell_style
        )]
    ]
    
    disclaimer_table = Table(disclaimer_data, colWidths=[6*inch])
    disclaimer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.orange),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 1), (0, 1), colors.lightyellow),
        ('TOPPADDING', (0, 1), (0, 1), 15),
        ('BOTTOMPADDING', (0, 1), (0, 1), 15)
    ]))
    
    story.append(disclaimer_table)
    story.append(Spacer(1, 20))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    story.append(Paragraph("Generated by AI Healthcare Assistant | For Medical Reference Only", footer_style))
    story.append(Paragraph(f"Report ID: {report_id} | Generated: {current_time}", footer_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.read()

def format_analysis_content(content):
    """Format analysis content for better table display"""
    if not content:
        return ""
    
    lines = content.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if line:
            if line.startswith('•') or line.startswith('-'):
                formatted_lines.append(f"• {line[1:].strip()}")
            else:
                formatted_lines.append(line)
    
    return '<br/>'.join(formatted_lines)

def parse_analysis_sections(analysis):
    """Parse analysis text into organized sections"""
    sections = {
        'Symptom Analysis': '',
        'Potential Conditions': '',
        'Severity Assessment': '',
        'Doctor Consultation': '',
        'Immediate Recommendations': '',
        'Follow-up Care': ''
    }
    
    lines = analysis.split('\n')
    current_section = ''
    section_content = []
    
    for line in lines:
        line = line.strip()
        
        # Detect section headers
        if any(keyword in line for keyword in ['Symptom Analysis', 'Potential Conditions', 'Severity Assessment', 
                                              'Doctor Consultation', 'Immediate Recommendations', 'Follow-up Care']):
            # Save previous section
            if current_section and section_content:
                sections[current_section] = '\n'.join(section_content)
            
            # Start new section
            current_section = line.replace('**', '').replace(':', '').strip()
            section_content = []
        elif line and current_section and not line.startswith('**'):
            section_content.append(line)
    
    # Save last section
    if current_section and section_content:
        sections[current_section] = '\n'.join(section_content)
    
    return sections

def generate_appointment_pdf_content(booking_details):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.darkblue,
        alignment=TA_CENTER,
        spaceAfter=30
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.darkgreen,
        spaceBefore=20,
        spaceAfter=12
    )
    
    urgent_style = ParagraphStyle(
        'UrgentStyle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.red,
        alignment=TA_CENTER,
        spaceBefore=10,
        spaceAfter=10,
        borderWidth=2,
        borderColor=colors.red,
        leftIndent=20,
        rightIndent=20,
        topPadding=10,
        bottomPadding=10
    )
    
    # Build PDF content
    story = []
    
    # Header with clinic info
    clinic_info = booking_details.get('clinic_info', {})
    story.append(Paragraph("🏥 AI HealthCare Clinic", title_style))
    story.append(Paragraph("Medical Appointment Confirmation", styles['Heading2']))
    story.append(Spacer(1, 10))
    
    # Clinic contact info
    if clinic_info:
        story.append(Paragraph(f"📍 {clinic_info.get('address', '123 Medical Center Drive')}", styles['Normal']))
        story.append(Paragraph(f"📞 {clinic_info.get('phone', '+1 (555) 123-CARE')}", styles['Normal']))
        story.append(Paragraph(f"📧 {clinic_info.get('email', 'appointments@healthcareai.com')}", styles['Normal']))
    
    story.append(Spacer(1, 20))
    
    # Urgency alert if high priority
    if booking_details.get('urgency', '').lower() == 'high':
        story.append(Paragraph("🚨 <b>HIGH PRIORITY APPOINTMENT</b> 🚨", urgent_style))
        story.append(Spacer(1, 15))
    
    # Confirmation message
    story.append(Paragraph("✅ <b>APPOINTMENT SUCCESSFULLY BOOKED</b>", header_style))
    story.append(Spacer(1, 20))
    
    # Appointment details table with better organization
    appointment_header = [
        [Paragraph("📋 <b>APPOINTMENT DETAILS</b>", 
                  ParagraphStyle('AppointmentHeader', parent=styles['Normal'], fontSize=14, textColor=colors.white, 
                               alignment=TA_CENTER, fontName='Helvetica-Bold')), ""]
    ]
    
    appointment_data = [
        ['🆔 Appointment ID:', booking_details.get('appointment_id', 'N/A')],
        ['👤 Patient Name:', booking_details.get('patient_name', 'N/A')],
        ['📞 Phone Number:', booking_details.get('phone', 'N/A')],
        ['📧 Email:', booking_details.get('email', 'Not provided')],
        ['📅 Appointment Date:', booking_details.get('date', 'N/A')],
        ['🕐 Appointment Time:', booking_details.get('time', 'N/A')],
        ['⚠️ Priority Level:', booking_details.get('urgency', 'Medium')],
        ['✅ Status:', booking_details.get('status', 'Confirmed')],
        ['📋 Booked On:', booking_details.get('booking_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))]
    ]
    
    # Combine header and data
    full_appointment_data = appointment_header + appointment_data
    
    appointment_table = Table(full_appointment_data, colWidths=[2.5*inch, 3.5*inch])
    appointment_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
        ('SPAN', (0, 0), (1, 0)),
        ('BACKGROUND', (0, 1), (0, -1), colors.lightblue),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    
    story.append(appointment_table)
    story.append(Spacer(1, 25))
    
    # Medical information table
    if booking_details.get('symptoms') or booking_details.get('analysis_summary') or booking_details.get('notes'):
        story.append(Paragraph("🩺 MEDICAL INFORMATION", header_style))
        
        medical_data = [
            [Paragraph("🩺 <b>MEDICAL SUMMARY</b>", 
                      ParagraphStyle('MedicalHeader', parent=styles['Normal'], fontSize=12, textColor=colors.white, 
                                   alignment=TA_CENTER, fontName='Helvetica-Bold')), ""]
        ]
        
        if booking_details.get('symptoms'):
            medical_data.append([
                Paragraph("<b>Chief Complaint:</b>", styles['Normal']),
                Paragraph(booking_details.get('symptoms'), styles['Normal'])
            ])
        
        if booking_details.get('analysis_summary'):
            medical_data.append([
                Paragraph("<b>AI Analysis:</b>", styles['Normal']),
                Paragraph(booking_details.get('analysis_summary'), styles['Normal'])
            ])
        
        if booking_details.get('notes'):
            medical_data.append([
                Paragraph("<b>Additional Notes:</b>", styles['Normal']),
                Paragraph(booking_details.get('notes'), styles['Normal'])
            ])
        
        # Add urgency information
        urgency_color = colors.red if booking_details.get('urgency', '').lower() == 'high' else colors.orange if booking_details.get('urgency', '').lower() == 'medium' else colors.green
        medical_data.append([
            Paragraph("<b>Priority Level:</b>", styles['Normal']),
            Paragraph(f"<b>{booking_details.get('urgency', 'Medium').upper()}</b>", 
                     ParagraphStyle('Urgency', parent=styles['Normal'], textColor=urgency_color, fontName='Helvetica-Bold'))
        ])
        
        medical_table = Table(medical_data, colWidths=[1.5*inch, 4.5*inch])
        medical_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
            ('SPAN', (0, 0), (1, 0)),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('LEFTPADDING', (0, 1), (-1, -1), 8),
            ('RIGHTPADDING', (0, 1), (-1, -1), 8)
        ]))
        
        story.append(medical_table)
        story.append(Spacer(1, 20))
    
    # Pre-appointment instructions table
    story.append(Paragraph("📋 PRE-APPOINTMENT INSTRUCTIONS", header_style))
    
    instruction_data = [
        [Paragraph("📋 <b>PREPARATION CHECKLIST</b>", 
                  ParagraphStyle('InstructionHeader', parent=styles['Normal'], fontSize=12, textColor=colors.white, 
                               alignment=TA_CENTER, fontName='Helvetica-Bold'))],
        [Paragraph("🕐 <b>Arrival:</b> Please arrive 15 minutes before your scheduled appointment time", styles['Normal'])],
        [Paragraph("🆔 <b>Documents:</b> Bring valid photo ID and insurance card (if applicable)", styles['Normal'])],
        [Paragraph("💊 <b>Medications:</b> Prepare complete list of current medications and dosages", styles['Normal'])],
        [Paragraph("📋 <b>Questions:</b> Write down all symptoms, concerns, and questions for the doctor", styles['Normal'])],
        [Paragraph("📞 <b>Confirmation:</b> You will receive a confirmation call within 24 hours", styles['Normal'])],
        [Paragraph("🚫 <b>Changes:</b> Give at least 24 hours notice for cancellation or rescheduling", styles['Normal'])]
    ]
    
    instruction_table = Table(instruction_data, colWidths=[6*inch])
    instruction_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ('LEFTPADDING', (0, 1), (-1, -1), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8)
    ]))
    
    story.append(instruction_table)
    
    story.append(Spacer(1, 20))
    
    # Urgency-specific instructions
    urgency_level = booking_details.get('urgency', 'Medium').lower()
    if urgency_level == 'high':
        story.append(Paragraph("🚨 URGENT CARE INSTRUCTIONS", header_style))
        story.append(Paragraph(
            "<b>This is a high-priority appointment.</b> If your symptoms worsen before your appointment, "
            "please contact emergency services immediately or visit the nearest emergency room. "
            "Do not wait for your scheduled appointment if you experience severe symptoms.",
            urgent_style
        ))
    elif urgency_level == 'medium':
        story.append(Paragraph("⚠️ MONITORING INSTRUCTIONS", header_style))
        story.append(Paragraph(
            "Please monitor your symptoms carefully. If they worsen significantly before your appointment, "
            "please call our clinic immediately. Seek emergency care if you experience severe symptoms.",
            styles['Normal']
        ))
    
    story.append(Spacer(1, 20))
    
    # Contact information
    story.append(Paragraph("📞 CONTACT INFORMATION", header_style))
    story.append(Paragraph("<b>For appointment changes or urgent questions:</b>", styles['Normal']))
    story.append(Paragraph("📞 Clinic Phone: +1 (555) 123-CARE", styles['Normal']))
    story.append(Paragraph("📧 Email: appointments@healthcareai.com", styles['Normal']))
    story.append(Paragraph("🌐 Website: www.healthcareai.com", styles['Normal']))
    story.append(Paragraph("🚨 Emergency: Call 911 or visit your nearest emergency room", styles['Normal']))
    
    story.append(Spacer(1, 30))
    
    # Footer with disclaimers
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_JUSTIFY,
        leftIndent=20,
        rightIndent=20,
        spaceBefore=10,
        spaceAfter=10,
        borderWidth=1,
        borderColor=colors.grey,
        topPadding=8,
        bottomPadding=8
    )
    
    story.append(Paragraph("<b>IMPORTANT DISCLAIMER:</b>", styles['Heading3']))
    story.append(Paragraph(
        "This appointment was scheduled based on AI analysis for informational purposes only. "
        "The AI assessment does not replace professional medical diagnosis. Please discuss all "
        "symptoms and concerns with your healthcare provider during your appointment.",
        disclaimer_style
    ))
    
    # Generation info
    current_time = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    story.append(Spacer(1, 15))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    story.append(Paragraph(f"Appointment slip generated on {current_time}", footer_style))
    story.append(Paragraph("AI HealthCare Assistant | Your Digital Health Companion", footer_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.read()

if __name__ == '__main__':
    app.run(debug=True) 