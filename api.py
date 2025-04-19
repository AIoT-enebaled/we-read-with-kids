from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, User, ChildProfile, Book, ReadingList, Challenge, Resource, LearningPath, PathActivity, ProgressAssessment
from datetime import datetime
import json

api_bp = Blueprint('api', __name__)

# Child Profile Routes
@api_bp.route('/child-profiles', methods=['GET'])
@login_required
def get_child_profiles():
    profiles = ChildProfile.query.filter_by(user_id=current_user.id).all()
    return jsonify({
        'profiles': [profile.to_dict() for profile in profiles]
    }), 200

@api_bp.route('/child-profiles/<int:profile_id>', methods=['GET'])
@login_required
def get_child_profile(profile_id):
    profile = ChildProfile.query.get_or_404(profile_id)
    
    # Verify ownership
    if profile.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    return jsonify(profile.to_dict()), 200

@api_bp.route('/child-profiles', methods=['POST'])
@login_required
def create_child_profile():
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'age', 'reading_level']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'Missing required field: {field}'}), 400
    
    # Create new profile
    new_profile = ChildProfile(
        user_id=current_user.id,
        name=data['name'],
        age=data['age'],
        reading_level=data['reading_level'],
        avatar_url=data.get('avatar_url')
    )
    
    # Add interests if provided
    if 'interests' in data and isinstance(data['interests'], list):
        new_profile.interests = data['interests']
    
    # Save to database
    db.session.add(new_profile)
    db.session.commit()
    
    # Generate initial learning path
    generate_learning_path(new_profile)
    
    return jsonify({
        'message': 'Child profile created successfully',
        'profile': new_profile.to_dict()
    }), 201

@api_bp.route('/child-profiles/<int:profile_id>', methods=['PUT'])
@login_required
def update_child_profile(profile_id):
    profile = ChildProfile.query.get_or_404(profile_id)
    
    # Verify ownership
    if profile.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    # Update fields
    if 'name' in data:
        profile.name = data['name']
    if 'age' in data:
        profile.age = data['age']
    if 'reading_level' in data:
        profile.reading_level = data['reading_level']
    if 'avatar_url' in data:
        profile.avatar_url = data['avatar_url']
    if 'interests' in data and isinstance(data['interests'], list):
        profile.interests = data['interests']
    
    # Save changes
    db.session.commit()
    
    return jsonify({
        'message': 'Child profile updated successfully',
        'profile': profile.to_dict()
    }), 200

@api_bp.route('/child-profiles/<int:profile_id>', methods=['DELETE'])
@login_required
def delete_child_profile(profile_id):
    profile = ChildProfile.query.get_or_404(profile_id)
    
    # Verify ownership
    if profile.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    # Delete the profile
    db.session.delete(profile)
    db.session.commit()
    
    return jsonify({
        'message': 'Child profile deleted successfully'
    }), 200

# Book Routes
@api_bp.route('/books', methods=['GET'])
def get_books():
    # Parse query parameters
    age_range = request.args.get('age_range')
    genre = request.args.get('genre')
    search_query = request.args.get('query')
    interactive_only = request.args.get('interactive', 'false').lower() == 'true'
    limit = int(request.args.get('limit', 20))
    
    # Build query
    query = Book.query
    
    if age_range:
        query = query.filter_by(age_range=age_range)
    if genre:
        query = query.filter_by(genre=genre)
    if interactive_only:
        query = query.filter_by(is_interactive=True)
    if search_query:
        query = query.filter(Book.title.ilike(f'%{search_query}%') | 
                            Book.author.ilike(f'%{search_query}%') |
                            Book.description.ilike(f'%{search_query}%'))
    
    # Execute query with limit
    books = query.limit(limit).all()
    
    return jsonify({
        'books': [book.to_dict() for book in books]
    }), 200

@api_bp.route('/books/featured', methods=['GET'])
def get_featured_books():
    # Get featured books (top rated or curated)
    featured_books = Book.query.order_by(Book.rating.desc()).limit(4).all()
    
    return jsonify({
        'featured_books': [book.to_dict() for book in featured_books]
    }), 200

@api_bp.route('/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    book = Book.query.get_or_404(book_id)
    return jsonify(book.to_dict()), 200

# Reading List Routes
@api_bp.route('/reading-list/<int:profile_id>', methods=['GET'])
@login_required
def get_reading_list(profile_id):
    # Verify profile belongs to user
    profile = ChildProfile.query.get_or_404(profile_id)
    if profile.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    # Get reading list items
    reading_list = ReadingList.query.filter_by(child_profile_id=profile_id).all()
    
    # Get book details for each item
    result = []
    for item in reading_list:
        book = Book.query.get(item.book_id)
        if book:
            item_dict = item.to_dict()
            item_dict['book'] = book.to_dict()
            result.append(item_dict)
    
    return jsonify({
        'reading_list': result
    }), 200

@api_bp.route('/reading-list', methods=['POST'])
@login_required
def add_to_reading_list():
    data = request.get_json()
    
    # Validate required fields
    if 'child_profile_id' not in data or 'book_id' not in data:
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Verify profile belongs to user
    profile = ChildProfile.query.get_or_404(data['child_profile_id'])
    if profile.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    # Verify book exists
    book = Book.query.get_or_404(data['book_id'])
    
    # Check if book is already in reading list
    existing = ReadingList.query.filter_by(
        child_profile_id=data['child_profile_id'],
        book_id=data['book_id']
    ).first()
    
    if existing:
        return jsonify({'message': 'Book already in reading list'}), 400
    
    # Add to reading list
    new_item = ReadingList(
        child_profile_id=data['child_profile_id'],
        book_id=data['book_id'],
        status=data.get('status', 'to-read')
    )
    
    db.session.add(new_item)
    db.session.commit()
    
    # Get book details
    item_dict = new_item.to_dict()
    item_dict['book'] = book.to_dict()
    
    return jsonify({
        'message': 'Book added to reading list',
        'reading_list_item': item_dict
    }), 201

@api_bp.route('/reading-list/<int:item_id>', methods=['PUT'])
@login_required
def update_reading_list(item_id):
    item = ReadingList.query.get_or_404(item_id)
    
    # Verify ownership
    profile = ChildProfile.query.get(item.child_profile_id)
    if profile.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    # Update status
    if 'status' in data and data['status'] in ['to-read', 'in-progress', 'completed']:
        item.status = data['status']
        
        # If status changed to completed, update completed_at
        if data['status'] == 'completed':
            item.completed_at = datetime.utcnow()
    
    # Update progress
    if 'progress_percentage' in data:
        progress = int(data['progress_percentage'])
        if 0 <= progress <= 100:
            item.progress_percentage = progress
    
    db.session.commit()
    
    # Get book details
    book = Book.query.get(item.book_id)
    item_dict = item.to_dict()
    item_dict['book'] = book.to_dict()
    
    return jsonify({
        'message': 'Reading list item updated',
        'reading_list_item': item_dict
    }), 200

@api_bp.route('/reading-list/<int:item_id>', methods=['DELETE'])
@login_required
def remove_from_reading_list(item_id):
    item = ReadingList.query.get_or_404(item_id)
    
    # Verify ownership
    profile = ChildProfile.query.get(item.child_profile_id)
    if profile.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    db.session.delete(item)
    db.session.commit()
    
    return jsonify({
        'message': 'Item removed from reading list'
    }), 200

# Challenge Routes
@api_bp.route('/challenges', methods=['GET'])
def get_challenges():
    challenges = Challenge.query.all()
    return jsonify({
        'challenges': [challenge.to_dict() for challenge in challenges]
    }), 200

@api_bp.route('/challenges/active', methods=['GET'])
def get_active_challenges():
    active_challenges = Challenge.query.filter_by(is_active=True).all()
    
    # If no active challenges found, return null or empty list
    if not active_challenges:
        return jsonify(None), 200
    
    # For demonstration, return the first active challenge
    active_challenge = active_challenges[0]
    
    # Add progress info if user is logged in
    if current_user.is_authenticated:
        profiles = ChildProfile.query.filter_by(user_id=current_user.id).all()
        if profiles:
            child_profile_id = profiles[0].id
            
            # Find participant info
            participant = db.session.query(challenge_participants).filter_by(
                challenge_id=active_challenge.id,
                child_profile_id=child_profile_id
            ).first()
            
            if participant:
                challenge_dict = active_challenge.to_dict()
                challenge_dict['progress'] = participant.progress
                challenge_dict['total'] = active_challenge.goal
                
                # Calculate days remaining
                now = datetime.utcnow()
                days_remaining = (active_challenge.end_date - now).days
                challenge_dict['days_remaining'] = max(0, days_remaining)
                
                return jsonify(challenge_dict), 200
    
    # If user not logged in or no profiles, return challenge with dummy progress
    challenge_dict = active_challenge.to_dict()
    challenge_dict['progress'] = 0
    challenge_dict['total'] = active_challenge.goal
    
    # Calculate days remaining
    now = datetime.utcnow()
    days_remaining = (active_challenge.end_date - now).days
    challenge_dict['days_remaining'] = max(0, days_remaining)
    
    return jsonify(challenge_dict), 200

@api_bp.route('/challenges/<int:challenge_id>/join', methods=['POST'])
@login_required
def join_challenge(challenge_id):
    data = request.get_json()
    
    # Validate child profile id
    if 'child_profile_id' not in data:
        return jsonify({'message': 'Child profile ID is required'}), 400
    
    # Verify profile belongs to user
    profile = ChildProfile.query.get_or_404(data['child_profile_id'])
    if profile.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    # Verify challenge exists and is active
    challenge = Challenge.query.get_or_404(challenge_id)
    if not challenge.is_active:
        return jsonify({'message': 'This challenge is not currently active'}), 400
    
    # Check if already joined
    existing = db.session.query(challenge_participants).filter_by(
        challenge_id=challenge_id,
        child_profile_id=data['child_profile_id']
    ).first()
    
    if existing:
        return jsonify({'message': 'Already joined this challenge'}), 400
    
    # Join the challenge
    new_participant = challenge_participants.insert().values(
        challenge_id=challenge_id,
        child_profile_id=data['child_profile_id'],
        progress=0,
        completed=False,
        joined_at=datetime.utcnow()
    )
    
    db.session.execute(new_participant)
    db.session.commit()
    
    return jsonify({
        'message': 'Successfully joined the challenge',
        'challenge': challenge.to_dict()
    }), 201

@api_bp.route('/challenges/progress/<int:challenge_id>', methods=['PUT'])
@login_required
def update_challenge_progress(challenge_id):
    data = request.get_json()
    
    # Validate required fields
    if 'child_profile_id' not in data or 'progress' not in data:
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Verify profile belongs to user
    profile = ChildProfile.query.get_or_404(data['child_profile_id'])
    if profile.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    # Verify challenge exists
    challenge = Challenge.query.get_or_404(challenge_id)
    
    # Update progress
    participant = db.session.query(challenge_participants).filter_by(
        challenge_id=challenge_id,
        child_profile_id=data['child_profile_id']
    ).first()
    
    if not participant:
        return jsonify({'message': 'Not participating in this challenge'}), 404
    
    # Update progress
    progress = int(data['progress'])
    
    # Check if challenge is completed
    completed = progress >= challenge.goal
    
    db.session.query(challenge_participants).filter_by(
        challenge_id=challenge_id,
        child_profile_id=data['child_profile_id']
    ).update({
        'progress': progress,
        'completed': completed
    })
    
    db.session.commit()
    
    return jsonify({
        'message': 'Challenge progress updated',
        'progress': progress,
        'completed': completed
    }), 200

# Resource Routes
@api_bp.route('/resources', methods=['GET'])
def get_resources():
    # Parse query parameters
    resource_type = request.args.get('type')
    category = request.args.get('category')
    age_range = request.args.get('age_range')
    
    # Build query
    query = Resource.query
    
    if resource_type:
        query = query.filter_by(type=resource_type)
    if category:
        query = query.filter_by(category=category)
    if age_range:
        query = query.filter_by(age_range=age_range)
    
    resources = query.all()
    
    return jsonify({
        'resources': [resource.to_dict() for resource in resources]
    }), 200

@api_bp.route('/resources/<int:resource_id>', methods=['GET'])
def get_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    return jsonify(resource.to_dict()), 200

# Learning Path Routes
@api_bp.route('/learning-paths/<int:profile_id>', methods=['GET'])
@login_required
def get_learning_paths(profile_id):
    # Verify profile belongs to user
    profile = ChildProfile.query.get_or_404(profile_id)
    if profile.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    # Get learning paths
    paths = LearningPath.query.filter_by(child_profile_id=profile_id).all()
    
    # Get activities for each path
    result = []
    for path in paths:
        path_dict = path.to_dict()
        activities = PathActivity.query.filter_by(learning_path_id=path.id).order_by(PathActivity.stage_number).all()
        path_dict['activities'] = [activity.to_dict() for activity in activities]
        result.append(path_dict)
    
    return jsonify({
        'learning_paths': result
    }), 200

@api_bp.route('/learning-paths/activities/<int:activity_id>', methods=['PUT'])
@login_required
def update_path_activity(activity_id):
    activity = PathActivity.query.get_or_404(activity_id)
    
    # Get path to verify ownership
    path = LearningPath.query.get(activity.learning_path_id)
    
    # Verify profile belongs to user
    profile = ChildProfile.query.get(path.child_profile_id)
    if profile.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    # Update status
    if 'status' in data and data['status'] in ['pending', 'in-progress', 'completed']:
        activity.status = data['status']
        
        # If completed, update is_completed flag
        if data['status'] == 'completed':
            activity.is_completed = True
            
            # Check if this is the current stage in the path
            if path.current_stage == activity.stage_number:
                # Advance to next stage if not at the end
                if path.current_stage < path.total_stages:
                    path.current_stage += 1
                    
                # Update path progress percentage
                completed_activities = PathActivity.query.filter_by(
                    learning_path_id=path.id,
                    is_completed=True
                ).count()
                
                total_activities = PathActivity.query.filter_by(
                    learning_path_id=path.id
                ).count()
                
                if total_activities > 0:
                    path.progress_percentage = int((completed_activities / total_activities) * 100)
                    path.last_updated = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'message': 'Activity updated',
        'activity': activity.to_dict()
    }), 200

# Progress Assessment Routes
@api_bp.route('/assessments/<int:profile_id>', methods=['GET'])
@login_required
def get_assessments(profile_id):
    # Verify profile belongs to user
    profile = ChildProfile.query.get_or_404(profile_id)
    if profile.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    # Get assessments
    assessments = ProgressAssessment.query.filter_by(child_profile_id=profile_id).order_by(
        ProgressAssessment.assessment_date.desc()
    ).all()
    
    return jsonify({
        'assessments': [assessment.to_dict() for assessment in assessments]
    }), 200

@api_bp.route('/assessments', methods=['POST'])
@login_required
def create_assessment():
    data = request.get_json()
    
    # Validate required fields
    if 'child_profile_id' not in data or 'reading_level' not in data:
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Verify profile belongs to user
    profile = ChildProfile.query.get_or_404(data['child_profile_id'])
    if profile.user_id != current_user.id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    # Create assessment
    new_assessment = ProgressAssessment(
        child_profile_id=data['child_profile_id'],
        reading_level=data['reading_level'],
        reading_fluency_score=data.get('reading_fluency_score'),
        comprehension_score=data.get('comprehension_score'),
        vocabulary_score=data.get('vocabulary_score'),
        notes=data.get('notes')
    )
    
    db.session.add(new_assessment)
    
    # Update child profile reading level
    profile.reading_level = data['reading_level']
    
    db.session.commit()
    
    # Generate new learning path based on assessment
    generate_learning_path(profile)
    
    return jsonify({
        'message': 'Assessment created successfully',
        'assessment': new_assessment.to_dict()
    }), 201

# Helper function to generate an AI-powered learning path
def generate_learning_path(profile):
    # This would normally involve AI, but for now we'll create a simple path
    
    # Create a new learning path
    path = LearningPath(
        child_profile_id=profile.id,
        title=f"Personalized Reading Journey for {profile.name}",
        description=f"A customized learning path designed for a {profile.age}-year-old reader at {profile.reading_level} level.",
        current_stage=1,
        total_stages=5,
        progress_percentage=0
    )
    
    db.session.add(path)
    db.session.flush()  # Get ID without committing
    
    # Create activities for the path
    activities = [
        {
            'title': 'Reading Assessment',
            'description': 'Complete an initial reading assessment to identify your strengths and areas for improvement.',
            'activity_type': 'assessment',
            'stage_number': 1
        },
        {
            'title': 'Vocabulary Building',
            'description': 'Practice with new words to expand your vocabulary.',
            'activity_type': 'exercise',
            'stage_number': 2
        },
        {
            'title': 'Guided Reading',
            'description': 'Read a story with interactive guidance to help with comprehension.',
            'activity_type': 'reading',
            'stage_number': 3
        },
        {
            'title': 'Comprehension Quiz',
            'description': 'Answer questions about the story to check your understanding.',
            'activity_type': 'quiz',
            'stage_number': 4
        },
        {
            'title': 'Creative Response',
            'description': 'Create your own story or drawing inspired by what you read.',
            'activity_type': 'creative',
            'stage_number': 5
        }
    ]
    
    for activity_data in activities:
        activity = PathActivity(
            learning_path_id=path.id,
            title=activity_data['title'],
            description=activity_data['description'],
            activity_type=activity_data['activity_type'],
            stage_number=activity_data['stage_number']
        )
        db.session.add(activity)
    
    db.session.commit()
    
    return path