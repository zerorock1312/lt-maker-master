from app.data.skill_components import SkillComponent

class Hidden(SkillComponent):
    nid = 'hidden'
    desc = "Skill will not show up on screen"
    tag = "attribute"

class ClassSkill(SkillComponent):
    nid = 'class_skill'
    desc = "Skill will show up on first page of info menu"
    tag = "attribute"

class Stack(SkillComponent):
    nid = 'stack'
    desc = "Skill can be applied to a unit multiple times"
    tag = "attribute"

class Feat(SkillComponent):
    nid = 'feat'
    desc = "Skill can be selected as a feat"
    tag = "attribute"

class Negative(SkillComponent):
    nid = 'negative'
    desc = "Skill is considered detrimental"
    tag = "attribute"

class Global(SkillComponent):
    nid = 'global'
    desc = "All units will possess this skill"
    tag = "attribute"
