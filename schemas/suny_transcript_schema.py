from pydantic import BaseModel, Field
from typing import Optional, List
from .base import BaseDocumentSchema

class CourseSchema(BaseModel):
    course_code: Optional[str] = Field(None, description="Course Code (e.g., BUS-110)")
    course_name: Optional[str] = Field(None, description="Course Name")
    credits: Optional[float] = Field(None, description="Credits/Hours")
    gpa: Optional[float] = Field(None, description="GPA or Grade points")

class SUNYTranscriptSchema(BaseDocumentSchema):
    document_type: str = "SUNY Academic Transcript"
    student_name: Optional[str] = Field(None, description="Student Full Name")
    student_id: Optional[str] = Field(None, description="Student ID")
    university_name: Optional[str] = Field("State University of New York", description="University/College Name")
    degree_level: Optional[str] = Field(None, description="Degree Level (e.g. Undergraduate)")
    degree_awarded: Optional[str] = Field(None, description="Degree(s) Awarded (e.g. Bachelor of Science)")
    degree_major: Optional[str] = Field(None, description="Degree Major(s)")
    ending_gpa: Optional[float] = Field(None, description="Cumulative/Ending GPA")
    date_awarded: Optional[str] = Field(None, description="Date Awarded")
    courses: List[CourseSchema] = Field(default_factory=list, description="Courses taken")
