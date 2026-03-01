import httpx
from bs4 import BeautifulSoup
import json
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

def fetch_bteb_result(roll_number, course_type="engineering"):
    """
    Fetches student results from btebresultscare.com
    
    Args:
        roll_number (str): The student's roll number
        course_type (str): Type of course (default: 'engineering')
        
    Returns:
        dict: Parsed result data or error message
    """
    url = "https://btebresultscare.com/wp-admin/admin-ajax.php"
    
    payload = {
        "action": "search_student_result",
        "roll_number": roll_number,
        "course_type": course_type
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://btebresultscare.com",
        "Referer": "https://btebresultscare.com/",
        "Sec-CH-UA": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
        "Sec-CH-UA-Mobile": "?1",
        "Sec-CH-UA-Platform": '"Android"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=1, i"
    }

    try:
        with httpx.Client(http2=True) as client:
            response = client.post(url, data=payload, headers=headers, timeout=30.0)
        
        if response.status_code != 200:
            return {"error": f"Server returned status code {response.status_code}", "raw": response.text}
        
        html_content = response.text
        if html_content == "0" or "not found" in html_content.lower():
            return {"error": "Result not found.", "raw": html_content}

        soup = BeautifulSoup(html_content, 'html.parser')
        result = {
            "roll": roll_number,
            "info": {},
            "semesters": [],
            "raw": html_content
        }
        
        header = soup.find('div', class_='result-header')
        if header:
            ps = header.find_all('p')
            result["info"]["course"] = ps[0].get_text(strip=True) if len(ps) > 0 else "N/A"
            result["info"]["institute"] = ps[1].get_text(strip=True) if len(ps) > 1 else "N/A"
            congrats = header.find('div', class_='congratulations')
            result["info"]["status"] = "Passed" if congrats else "Referred/Pending"

        semester_boxes = soup.find_all('div', class_='semester-box')
        for box in semester_boxes:
            title_div = box.find('div', class_='semester-title')
            title = title_div.get_text(strip=True) if title_div else "Unknown Semester"
            gpa_div = box.find('div', class_='gpa')
            
            sem_data = {
                "title": title,
                "gpa": gpa_div.get_text(strip=True) if gpa_div else None,
                "referred_subjects": []
            }
            
            failed_subjects = box.find_all('div', class_='subject-failed')
            for sub in failed_subjects:
                for span in sub.find_all('span'):
                    span.decompose()
                sem_data["referred_subjects"].append(sub.get_text(strip=True))
                
            result["semesters"].append(sem_data)
            
        return result
    except Exception as e:
        return {"error": f"Request failed: {str(e)}", "raw": None}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/result')
def get_result():
    roll = request.args.get('roll')
    if not roll:
        return jsonify({"error": "Roll number is required"}), 400
    
    data = fetch_bteb_result(roll)
    return jsonify(data)

@app.route('/api/raw')
def get_raw_result():
    roll = request.args.get('roll')
    if not roll:
        return "Roll number is required", 400
    
    data = fetch_bteb_result(roll)
    if "raw" in data and data["raw"]:
        return data["raw"]
    return data.get("error", "Failed to fetch raw data"), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
        
        # Optionally save to a JSON file
        # with open(f'result_{roll}.json', 'w') as f:
        #    json.dump(data, f, indent=4)