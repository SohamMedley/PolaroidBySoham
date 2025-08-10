from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont
import io
import os
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Create uploads directory if it doesn't exist
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

class PremiumPolaroidProcessor:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Only two frame styles: Curvy (Apple-style) and Classic (Sharp edges)
        self.frame_styles = {
            'curvy': {
                'bg_color': (255, 255, 255),
                'frame_radius': 60,  # Radius for entire frame
                'photo_radius': 45,  # Radius for photo inside
                'shadow_blur': 15,
                'text_color': (80, 80, 80),
                'premium': True
            },
            'classic': {
                'bg_color': (255, 255, 255),
                'frame_radius': 0,   # No radius for frame
                'photo_radius': 0,   # No radius for photo
                'shadow_blur': 8,
                'text_color': (80, 80, 80),
                'premium': False
            }
        }
    
    def detect_and_crop_face(self, image_array):
        """Enhanced face detection with smarter, less aggressive cropping"""
        gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
        
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.05,
            minNeighbors=6,
            minSize=(50, 50),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        height, width = image_array.shape[:2]
        
        # Check if image is already square or close to square
        aspect_ratio = width / height
        is_nearly_square = 0.8 <= aspect_ratio <= 1.25
        
        if len(faces) > 0:
            # Use the largest and most centered face
            best_face = self.select_best_face(faces, width, height)
            x, y, w, h = best_face
            
            # Calculate face center
            face_center_x = x + w // 2
            face_center_y = y + h // 2
            
            if is_nearly_square:
                # Image is already nearly square, minimal cropping
                crop_size = min(width, height)
                
                # Position face slightly above center (upper third)
                target_y = crop_size // 3
                
                # Calculate crop coordinates to position face optimally
                crop_x = max(0, min(face_center_x - crop_size // 2, width - crop_size))
                crop_y = max(0, min(face_center_y - target_y, height - crop_size))
                
            else:
                # Image needs significant cropping to square
                # Use more conservative crop size to preserve context
                base_crop_size = min(width, height)
                
                # Adjust crop size based on face size (less aggressive)
                face_area = w * h
                image_area = width * height
                area_ratio = face_area / image_area
                
                if area_ratio > 0.25:  # Large face - use smaller crop
                    crop_size = int(base_crop_size * 0.85)
                elif area_ratio < 0.08:  # Small face - use full available area
                    crop_size = base_crop_size
                else:  # Medium face - moderate crop
                    crop_size = int(base_crop_size * 0.92)
                
                # Position face in upper third of the frame
                target_face_y = crop_size // 3
                
                # Calculate crop coordinates
                crop_x = max(0, min(face_center_x - crop_size // 2, width - crop_size))
                crop_y = max(0, min(face_center_y - target_face_y, height - crop_size))
            
            # Crop the image with face detected
            cropped = image_array[crop_y:crop_y + crop_size, crop_x:crop_x + crop_size]
            
        else:
            # No face detected - use center crop only if needed
            if is_nearly_square:
                # Keep original if nearly square
                crop_size = min(width, height)
                crop_x = (width - crop_size) // 2
                crop_y = (height - crop_size) // 2
            else:
                # Center crop for non-square images
                crop_size = min(width, height)
                crop_x = (width - crop_size) // 2
                crop_y = (height - crop_size) // 2
            
            # Crop the image without face detected
            cropped = image_array[crop_y:crop_y + crop_size, crop_x:crop_x + crop_size]
        
        return cropped
    
    def select_best_face(self, faces, width, height):
        """Select the best face based on size and position"""
        center_x, center_y = width // 2, height // 2
        best_face = None
        best_score = -1
        
        for (x, y, w, h) in faces:
            # Face center
            face_cx = x + w // 2
            face_cy = y + h // 2
            
            # Distance from image center (normalized)
            center_distance = np.sqrt((face_cx - center_x)**2 + (face_cy - center_y)**2)
            max_distance = np.sqrt(width**2 + height**2)
            center_score = 1 - (center_distance / max_distance)
            
            # Size score (larger faces preferred, but not too large)
            face_area = w * h
            image_area = width * height
            area_ratio = face_area / image_area
            size_score = min(area_ratio * 4, 1.0)  # Optimal around 25% of image
            
            # Combined score
            total_score = center_score * 0.6 + size_score * 0.4
            
            if total_score > best_score:
                best_score = total_score
                best_face = (x, y, w, h)
        
        return best_face or faces[0]
    
    def apply_advanced_filters(self, pil_image, filters):
        """Apply advanced photo filters"""
        # Apply brightness
        if filters.get('brightness', 100) != 100:
            enhancer = ImageEnhance.Brightness(pil_image)
            pil_image = enhancer.enhance(filters['brightness'] / 100)
        
        # Apply contrast
        if filters.get('contrast', 100) != 100:
            enhancer = ImageEnhance.Contrast(pil_image)
            pil_image = enhancer.enhance(filters['contrast'] / 100)
        
        # Apply saturation
        if filters.get('saturation', 100) != 100:
            enhancer = ImageEnhance.Color(pil_image)
            pil_image = enhancer.enhance(filters['saturation'] / 100)
        
        # Apply tint (magenta/green balance)
        tint = filters.get('tint', 50)
        if tint != 50:
            pil_image = self.apply_tint(pil_image, tint)
        
        return pil_image
    
    def apply_tint(self, image, tint):
        """Apply tint filter (0-100: 0=green, 50=neutral, 100=magenta)"""
        factor = (tint - 50) / 50  # -1 to 1
        
        if factor == 0:
            return image
        
        # Create color adjustment
        pixels = np.array(image)
        
        if factor > 0:  # Magenta tint
            pixels[:, :, 0] = np.clip(pixels[:, :, 0] * (1 + factor * 0.15), 0, 255)  # Red
            pixels[:, :, 2] = np.clip(pixels[:, :, 2] * (1 + factor * 0.15), 0, 255)  # Blue
            pixels[:, :, 1] = np.clip(pixels[:, :, 1] * (1 - factor * 0.1), 0, 255)   # Green
        else:  # Green tint
            pixels[:, :, 1] = np.clip(pixels[:, :, 1] * (1 + abs(factor) * 0.2), 0, 255)  # Green
            pixels[:, :, 0] = np.clip(pixels[:, :, 0] * (1 - abs(factor) * 0.1), 0, 255)  # Red
            pixels[:, :, 2] = np.clip(pixels[:, :, 2] * (1 - abs(factor) * 0.1), 0, 255)  # Blue
        
        return Image.fromarray(pixels.astype(np.uint8))
    
    def create_premium_polaroid_effect(self, image_array, filters=None):
        """Create premium polaroid effects WITHOUT vignette"""
        pil_image = Image.fromarray(image_array)
        
        # Resize to high quality
        pil_image = pil_image.resize((500, 500), Image.Resampling.LANCZOS)
        
        # Apply custom filters first
        if filters:
            pil_image = self.apply_advanced_filters(pil_image, filters)
        
        # Apply premium vintage effects
        # 1. Slight desaturation for vintage look
        enhancer = ImageEnhance.Color(pil_image)
        pil_image = enhancer.enhance(0.88)
        
        # 2. Boost contrast slightly
        enhancer = ImageEnhance.Contrast(pil_image)
        pil_image = enhancer.enhance(1.08)
        
        # 3. Add subtle warm tint
        warm_overlay = Image.new('RGB', pil_image.size, (255, 248, 220))
        pil_image = Image.blend(pil_image, warm_overlay, 0.06)
        
        # 4. Add premium film grain
        pil_image = self.add_premium_film_grain(pil_image)
        
        # NO VIGNETTE - REMOVED COMPLETELY
        
        return pil_image
    
    def add_premium_film_grain(self, image):
        """Add subtle, premium film grain"""
        width, height = image.size
        
        # Create fine noise array
        noise = np.random.normal(0, 6, (height, width, 3)).astype(np.int16)
        
        # Convert image to array
        img_array = np.array(image).astype(np.int16)
        
        # Add noise
        noisy = img_array + noise
        
        # Clip values
        noisy = np.clip(noisy, 0, 255).astype(np.uint8)
        
        return Image.fromarray(noisy)
    
    def create_rounded_rectangle_mask(self, size, radius):
        """Create a rounded rectangle mask"""
        mask = Image.new('L', size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([(0, 0), size], radius=radius, fill=255)
        return mask
    
    def create_styled_polaroid_frame(self, photo_image, frame_style='curvy'):
        """Create polaroid frame with PROPER curvy or classic style"""
        style = self.frame_styles.get(frame_style, self.frame_styles['curvy'])
        
        # Frame dimensions
        frame_width = 600
        frame_height = 750
        photo_size = 500
        
        # Calculate photo position
        photo_x = (frame_width - photo_size) // 2
        photo_y = 50
        
        # Create base polaroid frame
        polaroid = Image.new('RGB', (frame_width, frame_height), style['bg_color'])
        
        # Add paper texture
        polaroid = self.add_premium_paper_texture(polaroid, frame_style)
        
        # Add shadow for photo
        self.add_premium_shadow(polaroid, photo_x, photo_y, photo_size, style)
        
        # Apply rounded corners to photo if needed
        if style['photo_radius'] > 0:
            # Create rounded photo
            photo_mask = self.create_rounded_rectangle_mask(photo_image.size, style['photo_radius'])
            photo_rgba = photo_image.convert('RGBA')
            photo_rgba.putalpha(photo_mask)
            
            # Paste photo with rounded corners
            polaroid.paste(photo_rgba, (photo_x, photo_y), photo_rgba)
        else:
            # Paste photo without rounding
            polaroid.paste(photo_image, (photo_x, photo_y))
        
        # CRITICAL: Apply frame rounding for curvy style
        if frame_style == 'curvy' and style['frame_radius'] > 0:
            # Create mask for entire frame
            frame_mask = self.create_rounded_rectangle_mask(polaroid.size, style['frame_radius'])
            
            # Convert polaroid to RGBA and apply mask
            polaroid_rgba = polaroid.convert('RGBA')
            polaroid_rgba.putalpha(frame_mask)
            
            # Create final image with white background
            final_image = Image.new('RGB', polaroid.size, (255, 255, 255))
            final_image.paste(polaroid_rgba, (0, 0), polaroid_rgba)
            
            return final_image
        
        # Return classic style without frame rounding
        return polaroid
    
    def add_premium_paper_texture(self, image, frame_style):
        """Add premium paper texture"""
        width, height = image.size
        
        # Different textures based on style
        if frame_style == 'curvy':
            # Premium subtle texture
            noise_intensity = 8
        else:
            # Classic paper texture
            noise_intensity = 12
        
        # Generate texture
        texture = np.random.randint(-noise_intensity, noise_intensity, (height, width, 3))
        
        # Apply texture
        img_array = np.array(image).astype(np.int16)
        textured = img_array + texture
        textured = np.clip(textured, 0, 255).astype(np.uint8)
        
        return Image.fromarray(textured)
    
    def add_premium_shadow(self, polaroid, x, y, size, style):
        """Add premium shadow effect"""
        # Create shadow layer
        shadow_layer = Image.new('RGBA', polaroid.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)
        
        # Shadow parameters
        shadow_offset = 4
        shadow_blur = style['shadow_blur']
        shadow_opacity = 30 if style['premium'] else 40
        
        # Draw shadow with appropriate corners
        if style.get('photo_radius', 0) > 0:
            # Rounded shadow for curvy style
            shadow_draw.rounded_rectangle([
                x + shadow_offset, y + shadow_offset,
                x + size + shadow_offset, y + size + shadow_offset
            ], radius=style['photo_radius'], fill=(0, 0, 0, shadow_opacity))
        else:
            # Regular rectangular shadow for classic style
            shadow_draw.rectangle([
                x + shadow_offset, y + shadow_offset,
                x + size + shadow_offset, y + size + shadow_offset
            ], fill=(0, 0, 0, shadow_opacity))
        
        # Apply blur
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
        
        # Composite shadow
        polaroid.paste(shadow_layer, (0, 0), shadow_layer)

processor = PremiumPolaroidProcessor()

@app.route('/generate-polaroid', methods=['POST'])
def generate_polaroid():
    try:
        # Check if image file is present
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Get parameters
        frame_style = request.form.get('frame_style', 'curvy')
        filters_json = request.form.get('filters', '{}')
        
        # Validate frame style
        if frame_style not in ['curvy', 'classic']:
            frame_style = 'curvy'
        
        try:
            filters = json.loads(filters_json) if filters_json else {}
        except json.JSONDecodeError:
            filters = {}
        
        # Read and process the image
        image_bytes = file.read()
        
        # Convert to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return jsonify({'error': 'Invalid image file'}), 400
        
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Step 1: Detect face and crop to 1:1 ratio
        cropped_image = processor.detect_and_crop_face(image_rgb)
        
        # Step 2: Apply premium polaroid effects with filters (NO VIGNETTE)
        polaroid_photo = processor.create_premium_polaroid_effect(cropped_image, filters)
        
        # Step 3: Create styled polaroid frame with PROPER ROUNDING
        final_polaroid = processor.create_styled_polaroid_frame(polaroid_photo, frame_style)
        
        # Save to memory buffer with high quality
        img_buffer = io.BytesIO()
        final_polaroid.save(img_buffer, format='PNG', quality=98, optimize=True)
        img_buffer.seek(0)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"polaroid_{frame_style}_{timestamp}.png"
        
        return send_file(
            img_buffer,
            mimetype='image/png',
            as_attachment=False,
            download_name=filename
        )
        
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to process image', 'details': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy', 
        'message': 'Premium Polaroid Studio API is running!',
        'features': {
            'face_detection': True,
            'curvy_frames': True,
            'classic_frames': True,
            'premium_filters': True,
            'advanced_effects': True
        }
    })

@app.route('/frame-styles', methods=['GET'])
def get_frame_styles():
    """Get available frame styles"""
    styles = {
        'curvy': {
            'name': 'Curvy Premium',
            'description': 'Apple-style rounded corners with premium effects',
            'badge': 'Apple Style',
            'premium': True
        },
        'classic': {
            'name': 'Classic Sharp',
            'description': 'Traditional polaroid with sharp edges',
            'badge': 'Traditional',
            'premium': False
        }
    }
    
    return jsonify({'styles': styles})

if __name__ == '__main__':
    print("🚀 Starting Premium Polaroid Studio Backend...")
    print("📸 AI-powered face detection ready!")
    print("🎨 Curvy Apple-style frames available!")
    print("📐 Classic sharp-edge frames available!")
    print("✨ Premium effects and filters loaded!")
    print("🌟 Server running on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
