# 2025-i40-capabilities (1)

## Seite 1

1
Capabilities, Skills and Services
CSS Model Extensions and Engineering Methodology
DISCUSSION PAPER


# 2025-i40-capabilities (1)

## Seite 2

Contents
1.  Introduction ....................................................................................................................................................................................  4
1.1 Motivation ................................................................................................................................................................................................. 4
1.2 CSS Model and Method Overview ......................................................................................................................................................  5
2.  Methods ...........................................................................................................................................................................................  7
2.1 Motivation of Methods ..........................................................................................................................................................................  7
2.2 Methods for Determining Capabilities ............................................................................................................................................... 8
2.1.1 Describing Capabilities ............................................................................................................................................................  9
2.2.2 Assigning Capabilities ............................................................................................................................................................ 13
2.2.3 Deriving Capabilities............................................................................................................................................................... 15
3.  Application Examples – Validation of CSS Model and Methology  .......................................................................................  17
3.1 Use Case 1: Realization of a Shared Production Scenario using Capabilities, Skills and Services ....................................  17
3.1.1 Use Case Description ............................................................................................................................................................. 17
3.1.2 Methods .................................................................................................................................................................................... 17
3.1.3 Technology-Mapping ............................................................................................................................................................. 18
3.1.4 Outlining CSS Model Extensions  .......................................................................................................................................  19
 3.2 Use Case 2: A Framework for Capability- and Skill-based  Engineering and Manufacturing Control ............................. 20
3.2.1 Use Case Description ............................................................................................................................................................. 20
3.2.2 Methods .................................................................................................................................................................................... 20
3.2.3 Technology-Mapping ............................................................................................................................................................. 21
3.2.4 Outlining CSS Model Extensions  .......................................................................................................................................  22
 3.3 Use Case 3: Capabilities at Different Levels of Detail .................................................................................................................. 23
3.3.1 Use Case Description ............................................................................................................................................................. 23
3.3.2 Methods .................................................................................................................................................................................... 23
3.3.3 Technology-Mapping ............................................................................................................................................................. 24
3.3.4 Outlining CSS Model Extensions  .......................................................................................................................................  24
 3.4 Use Case 4: Electronics Component Manufacturing .................................................................................................................... 25
3.4.1 Use Case Description ............................................................................................................................................................. 25
3.4.2 Methods .................................................................................................................................................................................... 26
3.4.3 Technology-Mapping ............................................................................................................................................................. 27
3.4.4 Outlining CSS Model Extensions  .......................................................................................................................................  27
 3.5 Use Case 5: Production-as-a-service ............................................................................................................................................... 28
3.5.1 Use Case Description ............................................................................................................................................................. 28
3.5.2 Methods .................................................................................................................................................................................... 28
3.5.3 Technology-Mapping ............................................................................................................................................................. 29
3.5.4 Outlining CSS Model Extensions  .......................................................................................................................................  29
4.  Revision and Refinement of the CSS Model .............................................................................................................................  30
4.1 Refinement of Skill ...............................................................................................................................................................................  30
4.2 Revision of Service ................................................................................................................................................................................ 31
4.2.1 Element Relations ................................................................................................................................................................... 31
4.2.2 Service Properties ................................................................................................................................................................... 31
 4.3 Constraints of Capabilities and Services .......................................................................................................................................... 33
4.3.1 PropertyConstraint ................................................................................................................................................................. 33
4.3.2 TransitionConstraint ............................................................................................................................................................... 34
 4.4 Revised CSS Model ............................................................................................................................................................................... 35
5.  Conclusion and Outlook  .............................................................................................................................................................  36
 Annex A – Changes in the CSS model  .......................................................................................................................................  37
 Annex B – Stakeholder Personas  ...............................................................................................................................................  37
 Literature  ......................................................................................................................................................................................  56


# 2025-i40-capabilities (1)

## Seite 3

3
Abbreviations
AAS  Asset Administration Shell
AGV  Automated Guided Vehicle
AI   Artificial Intelligence
ANSI  American National Standards Institute
BatchML Batch Markup Language
BPMN  Business Process Model Notation
CDD  Common Data Dictionary
CSS   Capabilities, Skills & Services
EDIFACT Electronic Data Interchange for Administration, Commerce and Transport
EKA  Entwurf komplexer Automatisierungssysteme
HC20  Honeycomb 20
HSU  Helmut Schmidt University
HTTP  Hypertext Transfer Protocol
ICC   International Chamber of Commerce
ID   Identifier
IDTA  Industrial Digital Twin Association
MES  Manufacturing Execution System
MQTT  Message Queuing Telemetry Transport
ODP  Ontology Design Pattern
OPC UA  Open Platform Communication Unified Architecture
OvGU  Otto von Guericke University
OWL  Web Ontology Language
PAS  Publicly Available Specification
PLC  Programmable Logic Controller
PPR  Product Process Resource
RWTH  Rheinisch-Westfälische Technische Hochschule
SME  Small and Medium-Sized Enterprise
UN   United Nations
VDI  Verein Deutscher Ingenieure
XML  Extensible Markup Language


# 2025-i40-capabilities (1)

## Seite 4

4
1 Introduction
In the dynamic and ever-changing landscape of manu-
facturing, flexibility is crucial for success. Flexibility in
this context refers to the ability to handle a variety of
product variants within a single production facility, man-
age smaller batch sizes of different products, and reor -
ganize production orders with minimal effort. To meet
these demands, the Capabilities, Skills and Services (CSS)
model is used for implementing capability-based engi-
neering. This model, which extends the Product, Process
and Resource (PPR) paradigm, separates product design
from production engineering [1]. The first version of the
discussion paper [2] of the Plattform Industrie 4.0 work-
ing group "Semantics and Interaction of I4.0 Compo-
nents" , presented the CSS information model. It is the
basis and starting point for the present document.
Ongoing work and practical exploration of the defined
CSS model [1] depicted further necessary expansions
and refinement of it. One of the main focuses of the
authors in this discussion paper was on the design of a
methodology to develop capabilities.
The term capability plays a major role in the CSS model.
It shows that capability is the link between services on
the one side (e.g., to interact with other companies) and
skills on the other side (e.g., for transferring a planned
process into the real world). Until now, there are only a
few formal methods for developing capabilities. To close
this gap, Section 2 introduces a methodology for capa-
bility development. The overall method Determining
Capabilities is further subdivided into the underlying
methods Describing Capabilities for capabilities, Assign-
ing Capabilities to link capabilities with production
resources (offered capabilities) and Deriving Capabilities
to link capabilities to product specifications and process
descriptions (required capabilities).
The second main focus was on the implementation work
of the general CSS model in [2]. Section 3 presents five
different use cases that utilized the CSS model with dif -
ferent methods, e.g., Determining Capabilities, and tech-
nologies to show the general applicability of the model.
Each of the use cases look at the topic from different per-
spectives, so that each use case therefore features differ-
ent extensions of the model for a specific area of applica-
tion. The extensions result in a consolidated refinement of
the CSS model and are described in Section 4. All import-
ant changes from the first version of the CSS model to the
new version are documented in Annex A.
Section 5 summarizes the work and gives an outlook on
ongoing as well as future research work to continue
refining the CSS model and its associated methods to
bring it into industrial practice.
Annex B provides usage views to the capability and ser -
vice-based production. These fictitious persons and
their statements are generated by a generative AI. It is a
trial to provide a more comprehensive view to this
upcoming technology approach.
1.1 Motivation
An important trend in future manufacturing is the
requirement for faster reaction to market uncertainties,
resulting in the need for more flexibility in industrial
production. This flexibility concerns many different
aspects, e.g. the ability for fast introduction of new
products or product variants, which affects the Product
Lifecycle Management (PLM) process. Therefore, the
possibility to efficiently produce high-mix scenarios
under low-volume down to lot size one is necessary.
This requires new concepts for production control as
well as the ability to react to problems and disturbances
within a production and supply chains. All these chal-
lenges do not only require a new kind of cross-company
collaboration, such as shared production using market-
places, but also fast changeability of plants to efficiently
adapt a production setup to changed conditions.
Today’s production systems are limited to meet these
requirements, as typically, there is a tight coupling of
products and their required production process steps to
the production resources. There are no widely accepted
or used standards applicable over all productions sec -
tors for the generalized description of products, produc-
tion processes and functionalities of production
resources, which enable decoupling and differentiation
between these concepts and, as a result, a flexible rela-
tion between these elements. This challenge has at least
two dimensions. On the one hand, the distinction and
relationship between product features, needed pro-
cesses and process steps, provided and required func -
tionalities, available interfaces etc. is often not clear or
even not applied. On the other hand, there is a lack of
concepts for a machine-interpretable description of


# 2025-i40-capabilities (1)

## Seite 5

5
these concepts, which is restricting the ability to a
dynamic and flexible matching between the required
and offered functions and the derived automated deci-
sions in a production control system. This allows the
replacement of pre-programmed and pre-configured
control sequences by model-based control design. The
same is true for interfaces between production control
and resources. In the case of changes in the use of a
resource, no complex interventions in the control pro-
grams should be necessary. It should be possible to
adjust the functionalities provided by the resource to
changed requirements by configuration of the standard-
ized interface. The CSS model provides an approach how
to meet these challenges.
Within the CSS model, a capability is an implementa-
tion-independent specification of a function, whereas a
skill refers to the function implemented based on the
capability specification [2]. Producing products through
specific production procedures requires capabilities to
execute each step of the process. These required capa-
bilities must be matched with those provided by the
available production resources [2].
After the CSS model has been defined by the Plattform
Industrie 4.0 [2] the question remains how engineering
methods to describe, assign or derive capabilities of the
CSS model look. Furthermore, implementation experi-
ences from different use cases for the CSS model were
made and refinements have been applied to the existing
CSS model. Both the usage of the CSS model, especially
the capability description, and the refinements will be
described in this paper. In order to increase the rele-
vance of the CSS model, stakeholder analyses were car -
ried out which will be presented in detail in annex B.
These are intended to highlight the areas of application
and the added value of using the CSS model.[2]
1.2 CSS Model and
Method Overview
This section gives a recap of the simplified overview of
the CSS model that was introduced in [2]. The evolved
methods for Determining capabilities relate to this over-
view. The understanding of the meaning of the terms
capability, skill and service are vital for the remainder of
this document.
Therefore, below, a summary of the definitions accord-
ing to [2] is provided.
Capability
A capability provides an implementation-independent
specification of a function in industrial production
aimed at achieving an effect in the physical (normally in
production) or virtual world (for software functions that
only apply to a virtual representation). Capabilities spec-
ifying a production function refer to terms of actual
manufacturing methods (e.g. "drilling") and have proper-
ties (e.g. depth, diameter) as well as constraints (e.g. the
material type).
Capabilities are provided by production resources claim-
ing their ability to apply the function expressed and
required by a process as part of a productions functional
requirements.
The concept of a capability is related to the concepts of
skills, which contain further details at implementation
level like the invocation of automation functions and
services which offer capabilities in a supply chain net-
work, that way forming the business façade for
capabilities.
Skill
A skill constitutes an executable implementation of an
encapsulated (automation) function specified by a capa-
bility. Skills are provided by the resources and assets
within a manufacturing environment and foster the real-
ization of a capability. A capability may reference more
than one skill acting as an implementation of the capa-
bility. In order to facilitate the communication with
external systems, e.g., MES, skills are provided to expose
an interface providing access to their standardized state
machines and to skill parameters. Multiple skill inter -
faces per skill are possible, that way allowing integrators
to select an interface compatible to their respective
technology stack.


# 2025-i40-capabilities (1)

## Seite 6

6
Service
Services represent a set of capabilities in a business
sense, that way supplementing it with organizational
and commercial descriptions, e.g., delivery dates, costs,
certifications and boundary conditions.
A service requester will provide a specification of the
services in demand, as well as their respective properties
required. The service requester then is open to accept
proposals of service providers with matching conditions
and within the validity period of the request as well as of
the proposal.
A service provider offers own manufacturing capabilities
and possibly also capabilities of external partners inte-
grated into the own production processes. The proposed
services comprise the capabilities offered, are aimed at
fulfilling the services in demand, and form the basis of a
binding contract to execute one or multiple services.
The simplified overview in Figure 1 shows the relations
between product, process and resource of the PPR model
[2] and capability, skill and service of the CSS model.
The overview can be split into three levels, where every
element of the PPR model has a connection to one or
more elements of the CSS model. At the highest level
there is the product with its required services. Each
required service needs an offered service to fulfil the
product needs. The services can be assembled through
different capabilities that are defined by the process (sec-
ond level) and are realized by the skill of a resource (third
level). To obtain the capabilities for a product specifica-
tion or a process description, the method Deriving Capa-
bilities (Section 2.2.3) is introduced. The formal descrip-
tion of a capability is done by the method Describing
Capabilities (Section 2.2.1). After describing and deriving
capabilities, they must be linked to resources. This is
done by the method Assigning Capabilities (Section
2.2.2). The method Determining Capabilities encom-
passes all the aforementioned methods into one
workflow.
Figure 1: Simplified overview on most important aspects of the CSS model [2]


# 2025-i40-capabilities (1)

## Seite 7

7
2 Methods
Workflows to describe, assign, and derive capabilities
are important for the application of the CSS model. This
discussion paper presents a comprehensive method,
Determining Capability. It encompasses three technolo-
gy-independent methods designed to assist stakehold-
ers in the manufacturing sector with describing, assign-
ing, and deriving capabilities.
• The first method, Describing Capabilities, ensures for -
mal semantic descriptions of capabilities. This method
provides a structured approach for defining the capa-
bilities in manufacturing.
• The second method, Assigning Capabilities, elaborates
on linking these capabilities to specific production
resources, ensuring that the right capabilities are attri-
buted to the appropriate resources.
• The third method, Deriving Capabilities, focuses on
extracting capabilities from production specifications
or process descriptions.
The findings of this white paper were previously pre-
sented at the Symposium Entwurf komplexer Automatis-
ierungssysteme (EKA) as a contribution to foster discus -
sion within the community [3]. This discussion paper
publishes the revised version of these methods, aiming
to provide a robust framework for the industry and facil-
itate further dialogue and development. Furthermore,
the methods and applications from Section 3 establish
refinements for the CSS model, and are described in
Section 4.
2.1 Motivation of Methods
Determining the capabilities needed for product fabrica-
tion and finding a viable sequence of production steps
involves matching required capabilities with those
offered by production resources. Currently, there are no
methodologies that are both technology-agnostic and
versatile for the formal description of capabilities to
facilitate this matching process. These methodologies
have to phase multiple stakeholders which are involved
in the value chain from planning to operation. The basis
for the design of the methodologies was an analysis of
these involved partners. The Annex B provide a compre-
hensive overview of these stakeholders. To guide the
stakeholders, in the following section workflows are
given for formal descriptions of capabilities, for assign-
ments of capabilities to production resources and for
deriving capabilities from product specifications or pro-
cess descriptions.
Research in capability and skill-based manufacturing
systems emphasizes the importance of adaptability and
flexibility in manufacturing and the associated process
planning. Various modeling methods are used, such as
ontologies, and technologies such as OWL or Automa-
tionML. Nevertheless, challenges persist, including
inconsistent modeling and differing abstraction levels
[4]. Consequently, there is a need for a method to for -
mally describe capabilities, ideally agnostic to specific
technologies, thus facilitating its applicability for differ -
ent capability-based approaches.
Ontologies are often used for methodical modeling of
capabilities. However, approaches as in [5] primarily
focus on general capability modeling and lack the con-
sideration for Deriving capabilities from product specifi-
cations or process descriptions. Another method in [6]
automates the creation of a specific capability model but
is limited to specific tools and standards. Some
approaches utilize the Asset Administration Shell (AAS)
for modeling, as seen in [7], but lack specific methodol-
ogies for capability modeling. The authors of [8] high-
light the importance of incorporating engineering pro-
cesses and standards into capability models but do not
offer a specific method for the PPR perspective.


# 2025-i40-capabilities (1)

## Seite 8

8
2.2 Methods for
Determining Capabilities
The method Determining Capabilities entails the use of
the underlying methods for describing, assigning and
deriving capabilities. According to the workflow shown
in Figure 2, the user chooses between describing capa-
bilities formally, assigning capabilities to production
resources, or deriving capabilities from product specifi-
cations or process descriptions.
In the method Determining Capabilities various artifacts
(gray boxes in Figure 2) are used as inputs or outputs for
the underlying methods.
Before starting the method Describing Capability, it
should be checked if there is already a formal capability
description available, which solves a stated problem. If
the formal description is sufficient according to the
available criteria (see 2.2.1) it can be used to describe the
unresolved placeholders in the temporary capability list
(see following paragraph). If not, a new formal capability
description needs to be developed. The formal capabil-
1 according to IEC 61406-1.
ity description that is used as input or is newly devel-
oped as output of the method can be, for example a
Capability Description Submodel of the AAS or an ontol-
ogy. It can consider several standards such as DIN 8580
[9], TGL 25000 [10], ECLASS or customized function
descriptions.
Another artifact that serves as input and output for the
underlying methods Describing Capabilities, Assigning
Capabilities and Deriving Capabilities is the temporary
capability list. The temporary capability list contains the
capability placeholders which need to be treated by the
method Describing Capabilities. During the work, the
content of the capability list is processed by the meth-
ods' capability description, derive capability and assign
capability. The administration and implementation of
the temporary capability list are not defined in this white
paper, as several different technologies and processes
for administration can be applied. In this list, all formal
capabilities which needs to be described are available as
a key value pair: The key is the capabilities unique Iden-
tifier (ID) 1 and the value is the capabilities informal
name, e.g., “Drilling” . The list is used to avoid recursive
Figure 2: Workflow for the main method Determining Capabilities


# 2025-i40-capabilities (1)

## Seite 9

9
use of methods among each other. This allows, using
and identifying a named but, informally, incomplete or
non-existing capability description as a temporary arti-
fact by creating a temporary ID named placeholder. The
capabilities for these placeholders must be described in
the method Describing Capabilities so that the place-
holders can be resolved.
For a comprehensive understanding of the workflow
regarding the description of a capability, the underlying
method Describing Capabilities is used to formally
describe capabilities, see Section 2.2.1.
The method Assigning Capabilities is used for assigning
formally described capabilities to resources which are
applied in capability-based production approaches, see
Section 2.2.2. For this, method a production resource,
e.g., a machine or human, is used as input.
The method Deriving Capabilities allows the derivation
of capabilities from process descriptions or product
specifications for a possible automated match with
assigned capabilities of resources, see Section 2.2.3.
If no appropriate formal capability description in the
methods Assigning Capabilities or Deriving Capabilities is
found, a capability placeholder (with a unique ID) is cre-
ated. This placeholder is added to the temporary capa-
bility list, which will be formally described in the method
Describing Capabilities.
After the capability description, the activity Resolve all
existing capability placeholder follows. There, the place-
holders must be replaced with the final unique ID of the
newly formally described capability. This activity is
repeated as long as all capability placeholders are
resolved.
2.2.1 Describing Capabilities
The method Describing Capabilities is one of the under -
lying methods of the method Determining Capabilities.
As shown in Figure 3, the workflow of the method
Describing Capabilities includes the general activities for
a formal and semantic description of a capability.
The description of a capability specifies the context in
which the capability is applied. Depending on the con-
text, capabilities can differ in their descriptions and
properties, e.g., “grasping” a tomato in food industry or
“grasping” a component in manufacturing industry. The
context can be refined by analyzing a production process
or by comparing similar production processes, as well as
by interviewing stakeholders to identify experiences and
challenges.
In the following, a brief overview of the method Describ-
ing Capabilities is provided before each activity is
described in more detail in the underlying subsections,
in order to provide clarity and referencing. This includes
the artifacts not yet described.
To avoid duplicated descriptions within one domain (e.g.
within one company), existing formal capability descrip-
tions should be considered. Querying existing capability
descriptions could investigate databases such as triple
stores, AAS repositories or public sources like open
access ontologies.
If one of the identified existing formal capability descrip-
tions suits well as a placeholder of the temporary capa-
bility list which needs to be described, the process of
Describing Capabilities is finished. For this, the existing
formal capability description is checked regarding e.g.
property semantics and constraints (Figure 3). Currently,
the checking for existing capabilities is not described
and is to be elaborated in future work. The following
examples are intended to provide inspiration for the
checking process:
• Correct application domain
 o Does the application domain of the existing capabi-
lity suit my use case?
• Applied and existing standards
 o Do the applied standards of the existing capability
suit my use case and requirements?
 o Does the existing capability meet relevant standards
for my use case?
• Capability description name
 o Does the name of the existing capability fit to my
use case?
• Capability description properties
 o Does the existing capability contain all properties
that are needed for my use case?
• Capability constraints
 o Does the existing capability meet all constraints of
my use case?


# 2025-i40-capabilities (1)

## Seite 10

10
If no suitable existing capability is found, the next activ-
ity is to identify standards, sources, or references that
may contain information for the description of the capa-
bility. That could be e.g. DIN 8580 [9], TGL 25000 [10] or
any other standard describing manufacturing
functionalities.
Then, the capability concept is created, which includes
the symbolic definition2 of the capability description. In
further activities, the dependencies on other capabilities
are to be described. These include the generalization
and composition relationship to other capabilities. Also,
the property specification of capabilities with its con-
straints will be considered. Finally, semantic formaliza-
tion is provided for further matching between required
capabilities derived from product specification or pro-
cess descriptions and offered capabilities assigned to
production resources.
2 Representation of something, such as word, images, sounds gesture, or any other sensory stimuli that convey meaning.
Therefore, the formalized capability description is used
for the following methods to either assign a capability to
a production resource or to derive a capability from a
product specification or a process description.
2.2.1.1 Identify existing capability
To avoid redundant capability descriptions, the existing
formal capability descriptions should first be checked to
see whether the capability already exists. Subsequently,
if a capability placeholder is identified, it should be
checked against the existing formal capability descrip-
tions if it matches the capability to be created. If the
check isn’t successful, a thorough examination of other
capability descriptions is warranted to ascertain whether
they encapsulate the desired capability placeholder but
are listed under a different (synonymous) name. In this
case, the name of the capability placeholder in the tem-
porary capability list should be reconsidered.
Figure 2: Workflow for the main method Determining Capabilities


# 2025-i40-capabilities (1)

## Seite 11

11
Databases such as triple stores, AAS repositories, or
publicly available sources including open access ontolo-
gies help in the search of suitable formal capabilities.
2.2.1.2 Identify Standards/Sources/References
If one of the identified existing capability descriptions
suits well to the capability placeholder which needs to
be described, the method of Describing Capabilities is
finished. For this, a capability description from an alter -
native database is checked in corresponding steps of the
method Describing Capabilities. If the validation is suc -
cessful, the capability placeholder is resolved in the
superior method Determining Capabilities.
In the field of engineering and manufacturing, compli-
ance with established standards and references is crucial
to ensure consistent quality and reliability of capabilities
and processes. One such recognized standard is DIN
8580, which defines terminology for manufacturing pro-
cesses. DIN 8580 divides all types of manufacturing pro-
cesses into six main groups. In addition, TGL 25000 is a
standard that provides description of unit operations in
process manufacturing by two distinct classification
schemas. The first schema organizes unit operations
based on the physical state of the materials being pro-
cessed, while the second schema arranges them accord-
ing to theoretical principles in chemical engineering. In
general, with these sources and others, functional
descriptions can be identified.
2.2.1.3 Create capability concept
A capability concept has to constitute an explicit and
formal model for a functionality described by a capabil-
ity. It is explicit in the sense that unique symbols are
used with all attributes, properties, constraints, general-
izations and conditions, in order to describe the capabil-
ity. Most notably, being explicit entails that all knowl-
edge required for automated processing must be
provided, and not implicit background knowledge is
required. It is formal in the sense that the representation
is machine-readable, -processable and -interpretable.
Moreover, the representation shall be shareable, mean-
ing that it can be used by different people or agents.
Shareability can be achieved by agreeing on a standard-
ized representation format. (The requirements of a
capability concept are close to the attributes Studer,
Benjamins and Fensel use in their frequently cited defi-
nition of ontology [11], making ontologies an ideal can-
didate to realize the capability concept.)
2.2.1.4 Define semantic capability symbol
The semantics of the capability symbol will be defined in
this activity, e.g., drilling serves as symbol for the afore-
mentioned thought and is added to the formal capabil-
ity description.
2.2.1.5 Identify capability generalization
For example, a required capability may be described in a
more abstract form, while offered capabilities are
described more specifically. Therefore, a capability
description at different hierarchical levels can be
required. Consequently, different levels of modeling
depths are necessary for matching within capabili-
ty-based engineering. In order to describe the capabili-
ties at different hierarchical levels, it is necessary to
identify the capability generalization. Therefore, the
upper class (superclass) must be linked to the capability
to be described by using the aforementioned activity of
identifying existing capabilities. In this activity of identi-
fying generalized capabilities, it is possible that multiple
generalizations may be identified either symbolically,
which need to be described formally, or else identified
with a complete capability description. With a successful
identification of generalized capabilities, they have to be
referenced. In the case that neither a capability is iden-
tified symbolically nor a complete capability description,
the aforementioned activity to identify standards,
sources, or references is used to introduce a new formal
capability description and to connect an upper-class
capability from these other sources to the capability to
be described.
2.2.1.6 Identify capability composition
A capability can be composed of other capabilities. The
composition of capabilities is a concept that involves
combining two or more capabilities to create a new
capability. Analog to the activity of identifying the capa-
bility generalization, the aforementioned activity of
identifying existing capabilities and the activity to iden-
tify standards, sources, or references can be used to
identify capability compositions.
To illustrate this concept, consider a robotic operation
known as Pick & Place. The entire task of picking up an
object and placing it at a specified location can be
decomposed into two distinct capabilities: grasp and
positioning. The capability grasp focuses on the gripping
or grasping action, while the capability positioning
involves precisely locating the target placement
coordinates.


# 2025-i40-capabilities (1)

## Seite 12

12
The decomposed capabilities might involve specialized
components from different manufacturers. For instance,
the grasp function could utilize a robotic gripper or hand
manufactured by a company specializing in robotic
end-effectors, while the positioning function might rely
on precision motors and sensors provided by a separate
manufacturer specializing in motion control
technology.
When these capabilities are composed to form the com-
posed capability Pick & Place, a system integrator is con-
sidered. The system integrator is responsible for inte-
grating these individual components into a cohesive and
functional robotic system. This includes designing the
overall structure, implementing the control algorithms
that govern the coordinated actions of grasp and posi-
tioning, and ensuring seamless communication between
the various components. The composition of these
capabilities, denoted as Pick & Place, integrates the grip-
ping and positioning actions required for the overall
task, see Figure 4 (left). With this, the composition of
capabilities considers for example the view of system
integrators. Also, these components act as individual
independent capabilities, each contributing a unique
function to the overall system. In a hierarchical struc -
ture, a system developer can reference the capability
grasp within the broader context of the generalized
capability Pick & Place without necessarily knowing the
details of the decomposed capabilities at the same level,
such as positioning. This encapsulation allows for mod-
ular and efficient design, enhancing the clarity and man-
ageability of complex systems, see Figure 4 (right). In
general, this action of the method can be skipped, if a
capability is not composed of other capabilities.
3 https:/ /cdd.iec.ch/ (accessed: June 28th 2024)
4 https:/ /eclass.eu/eclass-standard/content-suche (accessed: June 28th 2024)
2.2.1.7 Specify capability properties
Properties are used to describe the capability in more
detail. They cover a broad spectrum from physical
dimensions to sustainability data. To derive the proper -
ties for the given capability, documents and manuals for
production machines can be referred to, as well as stan-
dards such as IEC CDD 3 (International Electrotechnical
Commission Common Data Dictionary) or ECLASS4.
While describing the properties, a check is made to see
whether the properties described are sufficient or need
to be refined further. In this case, the existing properties
are extended using the documents and standards
described above.
2.2.1.8 Specify capability constraints
Capabilities can be constrained by either property con-
straints or transition constraints. The constraints can be
created for any perspective of a general, a resource or pro-
cess-specific capability description in a first step. Both
constraint types can be specified by a condition with any
condition pre, post or invariant after the first step.
• Property constraints are defined by a property value
statement, which specifies the context in which a
capability may be applied. To determine this, one or
more properties can be used. For example, a capability
brick burning might only be applicable if a tempera-
ture range of 950°C – 1000 °C is reached and held in a
kiln while the bricks are burned. Therefore, the pro-
perty constraint applies pre (before) and invariant
(while) conditions on the property temperature.
• Transition constraints allow one to describe a depen-
dency of a capability on another capability. For exam-
ple, to cut a thread, it is first necessary to drill a hole.
Therefore, when utilizing the capability “Threading” , a
precondition for the capability “Drilling” might apply.
Figure 4: Capability composition example for Pick & Place considering different views shown in blue


# 2025-i40-capabilities (1)

## Seite 13

13
2.2.1.9 Formalize capability semantically
Semantic formalization of information involves the pro-
cess of representing data and knowledge in a structured
and unambiguous manner, utilizing formal languages
and frameworks such as ontologies or semantic web
technologies. Finally, semantic formalization has to be
provided to enable matching of required capabilities
(derived from, e.g., product specification or process
descriptions) and offered capabilities (assigned to pro-
duction resources). Therefore, the formalized capability
description is used for the following methods to either
assign a capability to a production resource or else to
derive a capability from a product specification or a pro-
cess description.
2.2.2 Assigning Capabilities
Assigning capabilities to operational resources is a sys -
tematic approach for manufacturers or operators of a
machine, to derive resource capability model instances,
in order to allow for advanced automated production
planning. Figure 5 shows the workflow of the method
Assigning Capabilities with their activities and artifacts.
Figure 5: Workflow for the method Assigning Capabilities


# 2025-i40-capabilities (1)

## Seite 14

14
To successfully assign capabilities to a production
resource, first the resource must be identified. The
resource and its environment (if necessary) are used in
the remainder of the method. Resources typically already
possess skills which allow them to interact with a prod-
uct. Those skills have to be extracted from the resource
to identify an effect the skills have on the product. A for-
mal approach to defining effects is published in [12].
With the effects gathered, capabilities can be identified
using available formal capability descriptions. Either a
capability is found for an effect, or no capability is found.
Using the formal capability, an adaptation of the formal
capability description is assigned to the resource. With-
out a given formal capability, a new capability place-
holder is created in the temporary capability list. The
placeholder is used to create a formal capability descrip-
tion, see Section 2.2.1.
2.2.2.1 Identify resource
The first activity involves identifying production
resources. In the scope of this activity, the description of
the production resource and its environment (if neces -
sary) is used for selection. By identifying the resource, it
can be selected, and its description can be acquired. For
acquiring the description, machine-readable descrip-
tions, e.g., formal information models such as an AAS, or
resource non-formal documentation, e.g., operation
manuals, are used. The information can be gathered by
using internal and external sources, e.g., a manufactur -
er’s product catalog.
2.2.2.2 Identify resource (skills)
Typically, resources have skills, which allows one to
operate them for the processing of products. Hence, the
identification of resource skills becomes paramount, as
skills serve as the executable implementations of encap-
sulated functions specified by capabilities [2]. As a pre-
requisite to the following activities, resource skill
descriptions are made available by using the skill descrip-
tions, e.g., by reading information models, such as Mod-
ule Type Package [13], PackML [14] or Control Compo-
nents [15]. The information gathered from the skill
description is used to extract further information to
determine the effect on the product by processing it in
the production resource.
5 The effect, as a formal element, is currently under research.
2.2.2.3 Identify effect for resource skill
A resource’s goal is to reach or achieve an effect after a
skill execution. The capability and the effect are deter -
mined by the resource’s description and the skill descrip-
tion. It is essential to ascertain the effect of each resource
so that the alternative solutions of the production
machines can be abstracted to a capability via a descrip-
tion (of the effect). Therefore, one goal of the production
resource is to impose an effect onto the product through
skill execution. The effect is described as a change
between two states5, e.g., the change of a product geom-
etry or a temperature change in a process.
2.2.2.4 Derive required information for capability
selection
For the selection of the capability to be assigned, further
information is required in addition to the effect descrip-
tion. This information is gathered from standards or
other documents describing processes or operations,
such as DIN 8580 [9] or TGL 25000 [10].
2.2.2.5 Select capability
Using the information derived in Section 2.2.2.4, the
capability must be selected from the available capabili-
ties, as explained in Section 2.2. The user must select the
best match, if there is more than one match. In addition,
when selecting the capability, attention must be paid to
whether the capability matches the behavior and effect
of the resource and whether the capability is sufficiently
described for the resource. Either the capability is identi-
fied for an effect, or the capability is not sufficient.
2.2.2.6 Create temporary capability placeholder
If the capability for an effect is not identified and a capa-
bility is not already formally described, a new capability
placeholder has to be created in the temporary capabil-
ity list, and it has to be assigned to the production
resource. The placeholder is used as a provisional entity
until a formal capability description for the given
resource is provided by the method Describing Capabili-
ties, see Section 2.2.1.
2.2.2.7 Adapt formal capability for resource
The formal capability selected in 2.2.2.5 can be adapted
to the aspects and requirements of the resource. This is
conducted by adding values for properties (e.g., for a
drilling machine the available drill diameters), creating
additional constraints and refining the assigned effect.


# 2025-i40-capabilities (1)

## Seite 15

15
2.2.2.8 Assign capability to resource
In case the capability for an effect is identified, and also
the capability is formally described, the capability can be
assigned to the production resource using the adapted
capability. For the use of the adapted capability descrip-
tion, the selected capabilities for the production resource
are made accessible in a capability description model,
e.g., the AAS Capability Description Submodel 6 or a
resource ontology.
2.2.3 Deriving Capabilities
In addition to the two underlying methods described
above, the third method focuses on extracting required
capabilities from existing descriptions of production
procedures or product properties, i.e. product specifica-
tions or process descriptions consisting of a logical
sequence of process steps for manufacturing the product.
6 https:/ /github.com/admin-shell-io/submodel-templates/tree/main/development/Capability/1/0
The workflow of the method Deriving Capabilities is
shown in Figure 6. In total, the method consists of nine
activities, which are described individually in the follow-
ing. The method starts with the identification of required
product specifications or process descriptions. After this
step, a branch follows, depending on whether capabili-
ties are to be derived from a product specification or a
process description. Effects are to be identified from
these product specifications or process descriptions.
Then suitable capabilities can be selected by considering
the existing formal capability descriptions. If a formal
capability is found for an effect, the capability descrip-
tion can be adapted to the product specification or pro-
cess description. In the other case, a new placeholder for
the later capability description needs to be added to the
temporary capability list. The placeholder is used to cre-
ate a formal capability description in the method Describ-
ing Capabilities, see Section 2.2.1.
Figure 6: Workflow for the method Deriving Capabilities


# 2025-i40-capabilities (1)

## Seite 16

16
2.2.3.1 Identify product specification(s) or process
description(s)
A product specification or process description is neces -
sary to derive required capabilities. The specification or
description may be available in various forms, such as a
computer-aided design (CAD) model, a digital twin, a
product data model, a recipe, a production plan, a pro-
cedure, a formal description of a process or other tech-
nical specifications. However, these specifications or
descriptions alone are not always sufficient to fully iden-
tify the required capabilities and their sequence of exe-
cution for manufacturing a product.
After identifying the specifications and descriptions, a
decision is made whether capabilities have to be derived
from a product specification or from a process descrip-
tion. The product can have a modular structure. Conse-
quently, the presence of product parts must be identi-
fied. A product part itself is a component of a product to
be manufactured. Therefore, a product part is consid-
ered equivalent to a product in this contribution. Fur -
ther, process(es) are either directly identified from pro-
cess description(s) or identified from product
specification(s) of a production plan to be manufactured.
Similarly, a process can be structured into process steps,
which also have to be identified. Existing recipes, proce-
dures, production plans or formal descriptions of the
process allow the identification of individual process
steps. To derive required capabilities from an existing
process description, it is essential to use an existing rec-
ipe, procedure or formal description of the process that
allows the identification of individual production steps.
Finding required capabilities from these identified pro-
cess steps requires the integration of process-relevant
information, similar to the situation with product speci-
fications. This information must precisely define the
specific characteristics and requirements of each pro-
cess step to ensure a correct translation into the associ-
ated capabilities.
2.2.3.2 Identify effect for product or process
The objective of the identified products is to ascertain
the effects on the product, thereby enabling the deriva-
tion of information about possible capabilities for man-
ufacturing the product via a description of the effect. An
effect imposed on a product can be, to give a specific
example, the change imposed by removing material to
make a desired hole in a piece of metal. The effect
description is an artifact that is used for deriving required
information regarding the capability selection. In addi-
tion to the effects on the product(s), the effects on the
process(es) (process steps) have to be identified. For
example, an effect that must be imposed onto the pro-
cess and the product can be their temperature, which
has to be within a certain range to remove material to
make the desired hole in the piece of metal. The effect is
described as a change between two states [12], e.g., the
change of a product geometry or a temperature change
in a process.
2.2.3.3 Derive required information for capability
selection
The gathered information, including that pertaining to
the identified effects as described in the effect descrip-
tion and to process-relevant information from standards
such as DIN 8580 [9] or TGL 25000 [10], must be consid-
ered in order to derive the required information for
capability selection.
2.2.3.4 Select capability
Analogously to the method Assigning Capabilities, the
formal capability has to be selected from existing formal
capability descriptions. Additionally, the formal capabil-
ity must be selected to determine whether the capabil-
ity aligns with the effect of the product specification or
the process description. The selection of a capability
from the formal capability descriptions depends on
whether the capability is identified as sufficient or insuf-
ficient for an effect. If there is a sufficient capability
description found, the selected formal capability descrip-
tion serves as the output for the step. If no sufficient
capability description is found, a capability placeholder
needs to be added to the temporary capability list.
2.2.3.5 Create temporary capability placeholder
In correspondence to the Assigning Capabilities method
Section 2.2.2.6, if the formal capability for an effect is not
identified, a new capability placeholder is created in the
temporary capability list. Accordingly, the placeholder is
to be used as a provisional entity until a formal capability
description for the derived capability is provided using
the method Describing Capabilities, see Section 2.2.1.
2.2.3.6 Adapt formal capability by using product
specification or process description
In cases where a formal capability description is found
that solves the desired effect, the selected formal capa-
bility description can be adapted to the product specifi-
cation or process description. The method of Deriving
capabilities ensures a structured derivation of capabili-
ties from product specifications or process
descriptions.


# 2025-i40-capabilities (1)

## Seite 17

17
3 Application Examples –
Validation of CSS Model and Methodology
This section provides an overview of five different use
cases. On the one hand, these use cases all use the CSS
model described in [2]. On the other hand, they look at
the topic from different perspectives. Each use case
therefore features different extensions of the model for
a specific area of application. The individual use cases
and the extensions made in each case are presented
below. The individual extensions are then used to derive
a consolidated refinement of the CSS model.
3.1 Use Case 1: Realization of a
Shared Production Scenario using
Capabilities, Skills and Services
3.1.1 Use Case Description
The vision of Production Level 4 describes resilience,
flexibility and sustainability in subsidiary and human-cen-
tered production. In this context, subsidiarity and
human-centered production means a decentralized
structure of autonomously acting production units with
a focus on the integrative consideration of human and
machine. Especially, the ability to react to unforeseen
events becomes a decisive competitive advantage for
enterprises. To achieve this, SmartFactory KL identifies a
need for a Shared Production where reconfigurable sup-
ply chains are created in a federation of trusted partners
that dynamically share manufacturing services over a
product lifecycle through standardized digital twins. [16]
As a prerequisite, this vision requires a manufacturer-in-
dependent, standardized structure of information mod-
els for the exchange of machine-readable and interpre-
table data (1), standardized communication for
automated negotiations and data exchange (2), as well
as a federated and secure data infrastructure in accor -
dance with European legislation (3). The combination of
AAS as a manufacture-independent information model
and the CSS model as machine-readable description of
manufacturing functions is the foundation for Smart-
FactoryKL’s Shared Production use case. In this scenario,
five distributed industrial demonstrators are used to
manufacture a model truck. [17]
3.1.2 Methods
In the context of the CSS model, the service as an inter-
face forms the basis for the flexibilization of supply
chains. By describing it, the various technology chains
can be identified in Shared Production and therefore
requests for quotations can be sent to the different
companies. To ensure effective pre-selection of compa-
nies, the service must contain information that goes
beyond the description of the production technology.
The selection and structuring of this information is
therefore based on PAS 1018:2002-12 (Publicly Avail-
able Specification) [18]. This is structured as follows:
• Quantity (e.g. number of units and component sizes)
• Place of performance of a service
• General conditions of a service (necessary technical
documents and optimization criteria based on time,
ecological or economic aspects)
• Other agreements (reference to possible standards or
warranties)
• Qualitative information (e.g. general tolerances)
• Information on terms of payment and delivery
• Time schedule (performance period, milestones or
contract duration)
• Specified price of the client (e.g. asking price or esti-
mated price)
In addition to the description of the commercial aspects,
the service is also defined as the means of providing the
offered capabilities. Therefore, in addition to the descrip-
tive characteristics set out in PAS 1018, reference was
also made to the specific capabilities offered by the ser-
vice. Various methods were established from the model-
ling methodology of CSS model.


# 2025-i40-capabilities (1)

## Seite 18

18
In this use case, the method Describing Capabilities is
used to formalize the capabilities 3D-Priniting, FullAuto-
matedAssembly, ManualAssembly, QualityControl, Rect-
angularStraight and Step1Pocket. Within the manufac -
turing industry, there are several approaches to
formalizing such descriptions. For example, DIN 8580
and the Siemens-CAD-NX file format could be used as
an input. For the capabilities, the concept is needed first,
which is generated in the first step using symbols. To
identify the properties of the capability, properties were
extracted from the NX features for the Rectangular -
Straight and Step1Pocket capabilities and used within
the capability description. The constraints were formal-
ized within the properties.
The Assigning Capability method is used for the Rectan-
gularStraight and Step1Pocket capabilities, among oth-
ers. In this case, the production resource corresponds to
a cell containing a robot in operation, a tool storage, and
a clamping device. The existing function implementa-
tions on the robot are used to identify the capabilities.
The effect can then be identified from the existing skill
descriptions. From this information, the formalized
capability descriptions can now be assigned to the
resource.
A formal product specification in the form of a CAD
model was used to generate a manufacturing process.
Using the method Deriving Capabilities, the process
steps are first identified, and the required capabilities are
derived from them. Once all the required capabilities
have been derived, they can be matched with the offered
capabilities.
Current research and development work within the
Industrial Digital Twin Association (IDTA) [19] is focus -
ing on the development of an AAS submodel to be able
to map the structural logic of a capability, also men-
tioned in Section 2.2.2.8. The published development
status of this model was used at the time of realization.
3.1.3 Technology Mapping
Prerequisites for implementing the CSS model are stan-
dardized information models and interfaces for indus -
trial assets at various enterprise levels. In the Shared
Production use case digital representations for products,
resources and factories are needed that implement the
CSS model. There are different requirements depending
on the layer, e.g., execution (skills), planning (capabili-
ties) and business negotiation (services). A schematic
representation is visualized in Figure 7. It describes
assets with their equipped AAS and associated
submodels.
Figure 7: Schematic representation of the assets and submodels used in SmartFactory KL’s Shared Production use case


# 2025-i40-capabilities (1)

## Seite 19

19
In the SmartFactory KL scenario, factories, products and
resources are represented with a digital passport. AAS is
used as vocabulary for the communication between dif-
ferent stakeholders, e.g., a service requester and a ser -
vice provider, due to vendor-independence and seman-
tics. In this context, Required and Assured Services
describe tender criteria such as cost, terms of payments,
delivery date and carbon footprint. Service descriptions
are used to find suitable manufacturers without consid-
ering the technical aspects based on a bidding process.
For technical considerations, Required and Offered
Capabilities are matched to find resources that might
implement the Required Capabilities. At this stage, the
matching procedure is more like a parameter compari-
son based on constraints to exclude resources that are
unsuitable. As a result, Offered Capabilities are realized
with associated skills that provide processes. The skills
are accessible with a Skill Interface and compromise of a
FeasibilityCheck, PreconditionCheck and SkillExecution
for evaluation in advance. This relates to resources’
states and mostly operational data. For skills, OPC UA
(Open Platform Communication Unified Architecture)
and OPC UA Companion Specifications are well-estab-
lished in automation technology and machine access.
FeasibilityCheck simulates a production process and cal-
culates estimated values for production time, produc -
tion costs and energy consumption. This data is used to
generate BillOfProcesses and offer a proposal as a ser -
vice offer. After the service requester’s acceptance, the
appropriate SkillExecution autonomously executes the
product.
3.1.4  Outlining CSS Model Extensions
For the analysis and evaluation of the CSS model, the
individual aspects of services, capabilities and skills are
discussed one by one:
The service is described as “description of the commer -
cial aspects and means of provision of offered capabili-
ties” [2]. However, it does not differentiate between the
properties describing the service and the properties
describing other CSS elements. For a better understand-
ing of the service subclass commercial properties could
be specified and further elaborated. Additionally, a ser -
vice will not provide each specific capability to (for
example) a marketplace but would only provide an
abstraction of capabilities. For example, instead of mill-
ing a pocket, a service would be provided to mill specific
materials under specific conditions. This connection
between capability and service, especially the cardinality
between service and capabilities on different abstraction
levels must be further investigated.
Until now, the capability is just described by capability
constraints. However, there can be different kinds of
constraints. There are constraints relating to specific
properties. For example, the depth of a hole can be pro-
vided in the range of 10 to 30 mm. There can also be
additional kinds of constraints between two or more
capabilities. These different concepts of constraints
should be further elaborated.
In the simplest case, services and capabilities can be
described by means of a textual description, as they are
implemented independently. However, the skill describes
the interaction with the physical world and executes a
function. Therefore, knowledge of how to parametrize,
execute and interpret behavior must be provided. Cur -
rently, the metamodel does not describe how to imple-
ment a skill. This impairs interoperability. Therefore,
elaboration on modeling the results, describing the
interface in more detail and declaring a set of state
machines could foster overall understanding.


# 2025-i40-capabilities (1)

## Seite 20

20
3.2 Use Case 2: A Framework for
Capability- and Skill-based
Engineering and Manufacturing
Control
3.2.1 Use Case Description
The use case of Helmut Schmidt University (HSU)
focuses on the two model aspects of capabilities and
skills. For these two aspects, a holistic framework is
being developed that allows capabilities and skills to be
used throughout the entire lifecycle of automated sys -
tems. Engineering methods are being developed in order
to embed the creation of a capability and skill model in
engineering processes. During operation, processes are
automatically planned based on capabilities and carried
out using skills.
For evaluation purposes at laboratory scale, both dis -
crete and process manufacturing plants are used. A
modular discrete manufacturing system and a modular
process manufacturing system were equipped with
capabilities and skills. The two manufacturing systems
can be connected by an Automated Guided Vehicle
(AGV) to show one combined use case.
In addition to this manufacturing use case, HSU also
investigates the use of capabilities and skills to control
teams of autonomous robots with different modalities.
For this purpose, a team of drones, rovers and autono-
mous ships, which must jointly fulfill a mission, is being
examined.
3.2.2 Methods
At HSU, both engineering methods for creating a capa-
bility and skill model and methods for applying the
model at operation time of automated systems are
being investigated. Only a brief overview of some of
these methods can be given here.
In order to define a capability description for a new or
existing system, a semi-automated method is applied
using a graphical modeling tool based on the VDI guide-
line 3682 [20]. This method creates a semantic capability
model, establishes composition relationships and speci-
fies properties and constraints. It therefore represents a
possible manifestation of the method Describing Capa-
bilities (see Section 2.2.1). Skills can then be developed
using a Java or a Python framework. Software develop-
ers can use these frameworks to implement the skill
behavior – a skill interface and the skill model is gener -
ated automatically. For skills implemented on a Pro-
grammable Logic Controller (PLC), an automated map-
ping approach can alternatively be used to automatically
generate the skill interface and model. And in case a
Module Type Package (MTP) already exists, there is also
an automated mapping approach to convert MTPs into
HSU’s skill model. During skill implementation, a capa-
bility is assigned to the skill and the associated resource
as described in the method Assigning Capabilities see
(Section 2.2.2). All these methods make it possible to
define capabilities and implement skills for a wide vari-
ety of systems and use cases.
To use the capability and skill model obtained with the
previously mentioned engineering methods, operation
methods have also been developed. Capability matching
is done using an artificial intelligence (AI) planning
approach that generates a constraint problem for all
provided capabilities as well as a product request or
required capability. The planning approach tries to find a
process plan of provided capabilities that achieves the
required ones.
An orchestration method based on Business Process
Model Notation (BPMN) is used to execute manufactur-
ing processes. With this method, manufacturing pro-
cesses can be modeled manually using the available
capabilities and skills. Alternatively, a result of the auto-
mated planning approach can be automatically trans -
formed into a BPMN process to enable execution.


# 2025-i40-capabilities (1)

## Seite 21

21
3.2.3 Technology Mapping
The core of HSU's work are ontologies in Web Ontology
Language (OWL) for describing both capabilities and
skills in one coherent model. These ontologies were
developed as a three-layer architecture, see Figure 8.
At the top level of this architecture is the CSS ontology,
an ontology that captures the CSS reference model pre-
sented in [2] in an ontological way. To be able to repre-
sent individual aspects of this model in a level of detail
required for implementations, the CSS ontology was
extended on two layers with individual ontologies,
so-called Ontology Design Patterns (ODPs), which are
all based on standards.
The first extension, the CaSk ontology is still domain-in-
dependent and reusable. However, it allows, for exam-
ple, processes or state machines to be modeled in detail
according to VDI guideline 3682 or PackML,
respectively.
7 https:/ /github.com/CaSkade-Automation/CSS can be used as a starting point to get to the other ontologies
The two ontologies on the lower level of the architec -
ture shown in Figure 8 allow for detailed modeling of
skills according to domain-specific aspects and technol-
ogies. On the one hand, the CaSkMan ontology extends
CaSk with ODPs for Describing capabilities and skills for
manufacturing. For example, CaSkMan uses an ontology
of manufacturing processes according to DIN 8580 as
well as an OPC UA ontology to model skill interfaces. On
the other hand, RoboCask is an ontology that is specially
tailored to the description of autonomous systems. It
features ODPs based on IEEE standards for autonomous
systems as well as ODPs for MQTT (Message Queuing
Telemetry Transport), a typical communication technol-
ogy in this area.
All ontologies of this architecture are available online 7
and allow for reuse at different points of granularity:
CaSkMan or RoboCaSk can directly be used for manu-
facturing and autonomous systems, respectively. Ontol-
ogies with individual extensions can be made, starting
from the CaSk ontology.
In HSU’s use cases, information modeled with these
ontologies is created during engineering and used for
both planning and execution. In order to model skill
interfaces and invoke skills, OPC UA, HTTP (Hypertext
Transfer Protocol) or MQTT can be used.
Figure 8: Capability and skill ontology architecture of HSU


# 2025-i40-capabilities (1)

## Seite 22

22
3.2.4 Outlining CSS Model Extensions
All ODPs of standards shown in Figure 8 (e.g., PackML,
DIN 8580, OPC UA) point to extensions of the original
CSS model. Numerous simple classes of the CSS model
were extended by information models in the form of
ODPs:
• The CSS class StateMachine is extended by the PackML
state machine model with all its states and transitions.
• The CSS class Property is extended by the model of
IEC 61360, a standard defining a metamodel for pro-
perties in detail.
• The CSS class Process is modeled in detail using an
ODP according to the VDI guideline 3682. This allows
one to depict processes consisting of multiple process
steps with their inputs and outputs. Furthermore,
ODPs for DIN 8580 and VDI 2860 [21] were used to
add taxonomies of manufacturing and handling types,
respectively.
• The CSS class Resource is subdivided into systems,
modules and components according to VDI 2206 [22].
• The CSS class CapabilityConstraint is modeled using
an ODP of OpenMath 8. This ODP can represent arbi-
trary mathematical expressions, e.g., to capture the
dependencies between two product properties.
• The CSS class SkillInterface is extended by three clas-
ses representing interfaces using OPC UA, HTTP and
MQTT. Details of these interfaces are modeled using
ODPs of these technologies, e.g., an ODP that allows
to model OPC UA information models in an ontology.
Subclasses for parameters are defined and in addition
to parameters, skills provide skill methods, which are
linked to a transition of a skill’s state machine.
8 https:/ /openmath.org/about/


# 2025-i40-capabilities (1)

## Seite 23

23
3.3 Use Case 3: Capabilities at
Different Levels of Detail
3.3.1 Use Case Description
The modular plant “Honeycomb” from the chair of auto-
mation and information systems at Rheinisch-West-
fälische Technische Hochschule (RWTH) Aachen Uni-
versity is used for modular production and automation
techniques demonstrating innovation and flexibility, see
Figure 9. The transformation of resource-independent
specifications into plant-specific master recipes can be
achieved with the CSS model. One example is a general
recipe based on the ANSI/ISA-88 (American National
Standards Institute/International Society of Automa-
tion) standard [23]. First, a specification is generated
independent of the specific plant or resource. Then, a
capability alignment is needed to find one or more
resources from the resource-independent recipe for the
production of a process product. Capability alignment
with the CSS model will be showcased by this modular
plant. In this use case, capabilities at different levels of
detail are considered, i.e., MixingOfLiquids is a general-
ized capability of Stirring and also of Circulating.
A skill-based implementation according to Control
Components and MTPs is currently in progress. The
aspects of services from the CSS model are not further
considered in this use case. In the following methods
from Section 2 are used to describe, assign and derive
capabilities.
3.3.2 Methods
In this use case, the method Describing Capabilities is
used to formally describe the capabilities of MixingOfLi-
quids, Stirring and Circulating. In the context of process
industry, existing capabilities are to be identified from
the temporary capability list and from the formalized
capability descriptions. For the formal description of the
capability MixingOfLiquids the TGL 25000 can be consid-
ered, which provides a description of the combining
operation. The concept for the capability MixingOfLiq-
uids is needed, which is first semantically created
through a symbol. Afterwards, the concept of the capa-
bility can be extended through identifying relations
regarding parent capabilities or through composed
capabilities. This MixingOfLiquids capability is described
by the properties of the aggregate state of the materials
and the corresponding density. Nevertheless, standards
for property description should be used, e.g., IEC 61360
and ECLASS. By specifying the constraints regarding the
properties, the formalized description can be finalized.
The method Assigning Capability is used for assigning
the formally described capabilities Stirring and Circulat-
ing, which are specialized capabilities of the capability
MixingOfLiquids. In this use case, the production
resource corresponds to the modular plant section Hon-
eycomb 20 (HC20). The existing function implementa-
tions are used to identify the skills, which can be avail-
able as skill descriptions, e.g., as MTP, Control
Component or PackML. The effect can be identified
from the skills, which are here stirring with a stirrer or
Figure 9: Capability alignment for Honeycomb demonstrator at RWTH Aachen University


# 2025-i40-capabilities (1)

## Seite 24

24
circulating the liquid in HC20. With the identified infor -
mation of the resource, the assigning of the formalized
capability description can be applied.
A formal process description in the form of a recipe is
used to produce a product. Process steps are identified
with the method Deriving Capabilities. For every identi-
fied process step, the required capability must be
derived. If the formal capability descriptions contain
capability information on distinct detail levels, e.g., gen-
eralized capability of a capability description, a matching
of required and offered capabilities on different abstrac-
tion levels can be applied.
With these methods, a capability matching of the
required capability MixingOfLiquids is possible to either
the offered capability Stirring or Circulating.
3.3.3 Technology Mapping
One technology that is applied for the capability descrip-
tion of the production resources is the AAS. The formal
description of a process is applied by implementing a
general recipe in Batch Markup Language (BatchML),
based on XML (Extensible Markup Language) and con-
forming to the ANSI/ISA-88 standard. OWL is used for
referencing process steps regarding required capabilities
within a formal process description.
3.3.4 Outlining CSS Model Extensions
For a more accurate matching between required and
offered capabilities, the term constraint is not suffi-
ciently detailed in the previous CSS model. A constraint
can be applied to a property of a capability, or it can be
applied to one capability that implies constraints on
another capability in its logical sequence. In the previous
CSS model, it was not clear how a constraint is to be
applied. Therefore, constrains between a property and a
capability as well as between capabilities need to be
distinguished.
With the introduced method Describing Capabilities the
workflow regarding capabilities at different detail levels
(abstract capabilities) and composed capabilities is
pointed out.


# 2025-i40-capabilities (1)

## Seite 25

25
3.4 Use Case 4: Electronics
Component Manufacturing
As a vendor of factory equipment and solutions, Sie-
mens produces electronics components for automation
solutions such as controllers. Here, a respective use case
for flexible production of electronics component is
presented.
3.4.1 Use Case Description
Siemens offers a plethora of electronics components for
factory automation and other areas to its customers,
including programmable logic controllers, motion con-
trol units, power supplies and many more. This section
describes a use case of the CSS model for supporting
manufacturing planners in electronics component
manu facturing, as it could be applied in some of the
many Siemens production sites.
To restrict the scope of the scenario, the focus is on the
final assembly of electronics components. This com-
prises steps such as the lasering of markings onto casing
parts, their assembly with printed circuit boards after
depanelling, and the final testing of their electronic
functionality. The required production setup is typically
partly automated and partly operated manually and
involves lasering stations, assembly robots, testing sta-
tions, etc. Figure 10 depicts such an exemplary and
greatly simplified production setup.
Due to an increasing demand for customization and
shared production scenarios, also electronics compo-
nent manufacturing aims to adopt principles from
Industrie 4.0 to support flexible manufacturing planning
and execution. Specifically, the concepts of explicit
descriptions of capabilities and skills are to be utilized
for realizing the typical lot size one scenarios. In this
sense, the production equipment is to be allocated to
operations for electronics component manufacturing
dynamically at a late point in time to give the manufac -
turing planner a tool for more flexibility. This can be
exploited in two phases of manufacturing. On the one
hand, the planner can be supported offline at planning
time by suggesting possible allocation decisions based
on the results of capability matching. On the other hand,
invocation of dynamically allocated production equip-
ment through skill interfaces can support the manufac -
turing execution phase in online production scenarios.
Also, a combination of the two is possible. The following
figure displays the principles of dynamic equipment
allocation based on capabilities and skills in the context
of electronics component manufacturing.
Figure 10: Production setup for electronics component manufacturing


# 2025-i40-capabilities (1)

## Seite 26

26
3.4.2 Methods
In this use case, both the elements of capabilities and
skills are utilized. Capabilities are used for finding suit-
able candidate machines as part of manufacturing plan-
ning, whereas skills are used for abstracting the invoca-
tion of production functionality at the level of
harmonized APIs. As for capabilities, all the methods of
Describing Capabilities, Assigning Capabilities and Deriv-
ing Capabilities find their application in this scenario.
In a Siemens internal project, a tool for the management
of capabilities and skills was developed. This capability
configurator tool provides a graphical user interface tar-
geting manufacturing planners. They can author capa-
bilities and their constraints, and assign them to produc-
tion operations as requirements or to production
equipment as offers. This corresponds to the methods of
Describing and Assigning Capabilities. As for Deriving
Capabilities, the tool also supports the automated gen-
eration of capability templates from other artifacts such
as Bill-of-Material (BoM) and Bill-of-Process (BoP) data
records. Likewise, the tool supports the authoring of skill
interfaces and their assignment to equipment and to the
realized capabilities. In a producibility exploration view,
they can interactively match capabilities offered by
equipment against those required by operations to test
producibility of a product on a production line. In case of
mismatches, they can explore for reasons making use of
the built-in explanation features. The following Figure
shows a screenshot of this producibility view. The tool
can also be used to define skill interfaces and assign
them to machines. These definitions are initially
protocol-independent.
Figure 11: Dynamic equipment allocation principal based on capabilities
Figure 12:Capability configurator tool


# 2025-i40-capabilities (1)

## Seite 27

27
3.4.3 Technology Mapping
For capabilities, semantic descriptions in OWL are uti-
lized as an implementation technology. They refer to
OWL ontologies capturing background knowledge of
the manufacturing domain, such as the PPR paradigm,
pre-defined types for factory equipment or class hierar-
chies for standards such as DIN 8580 or VDI 2860. The
representation and formalization of capabilities in OWL
allows for their automated matching by means of stan-
dard reasoning tools without the need for development
of specific matchmaking algorithms. In [24], the mechan-
ics of this representation and reasoning-based matching
is described in more detail for an automotive use case.
The major advantage of this mapping to ontologies is
the possibility to cope with complex conceptual models
when describing manufacturing scenarios, in which
capability descriptions go beyond simple lists of proper-
ties. As an example of where this is beneficial, consider
the manufacturing step of assembling the various casing
parts together with the printed circuit board. A capabil-
ity description for this assembly step needs to constrain
a property like the length of the parts to be assembled.
As each of the assembly parts has its own length, this
can best be represented by length being the property of
an abstract type like MechanicalPart in the ontology that
is then inherited by more specific parts like Lid or Case.
In this way, the modeler can refer to the length of any
specific part when formulating constraints without the
need to introduce multiple length-properties for differ -
ent parts in a flat list of capability properties.
For skills, different realizations of skill interfaces with
OPC UA are provided as the main technology for com-
munication and information modelling of data struc -
tures. Based on the general definitions of skill interfaces
created by the same tool as used for capability model-
ling, interfaces can be generated for the skill implemen-
tation side (e.g. for PLCs) as well as for the invocation
side (e.g. Manufacturing Execution Systems). Using this
mechanism skill interfaces can be tailored to the specific
protocols, as well as needs or limitations of an environ-
ment (e.g. using OPC UA methods) based on the same
general interface definition.
3.4.4 Outlining CSS Model Extensions
Basically, the CSS model suffices as is for this use case.
However, extensions could bring up further require-
ments on expressing more complex relationships
between capabilities and skills that are beyond the cur -
rent “isRealizedBy”-relationship. For example, a need for
distinguishing the composition of a capability’s realiza-
tion by multiple skills from a situation where multiple
sets of realizing skills represent alternatives and com-
plete realizations. For the skill implementation, different
specializations of the CSS model are provided (e.g. with
state machines of different complexity) to adapt the skill
implementation to execution platform restrictions and
application requirements.


# 2025-i40-capabilities (1)

## Seite 28

28
3.5 Use Case 5:
Production-as-a-service
3.5.1 Use-Case Description
As part of the VWS vernetzt9 project, a demonstrator has
been created at the Otto-von-Guericke University Mag-
deburg (OvGU) that shows, among other things, the Pro-
duction-as-a-Service use case. A product to be manufac-
tured organizes its own production decentrally by
tendering or negotiating the services required for pro-
duction, e.g. drilling or honing. As the product has no
intelligence of its own, it is equipped with a digital twin
in the form of a proactive AAS with decision-making
capabilities. This AAS contains the process steps and
their requirements that are necessary for production,
and represents the product in negotiations as a service
requester.
Machines and factories are also equipped with proactive
AASs that know the capabilities of the machines and
their properties. They represent the machine as a service
provider. When the service providers receive requests of
the service requester, these are evaluated by a feasibility
check and, if the result is positive, the service provider
replies an offer. The service requester waits for a certain
time or for a certain number of offers and, depending on
the target function, decides on the most suitable offer
and accepts it. Once the transport has been negotiated,
the selected service provider carries out the agreed ser -
vice and provides information on the status. If several
processes are required for production, the next service is
then negotiated.
9 https:/ /vwsvernetzt.de/
3.5.2 Methods
The OvGU demonstrator comprises the application and
modelling of the elements’ capability, skill and service.
A service is offered, which contains both technical and
commercial properties. The technical properties are
encapsulated by the capability and serves for the feasi-
bility check. Skills are used to carry out the negotiated
services. The method Describing Capabilities and Assign-
ing Capabilities were successfully used to model the
capabilities in this use case. The method Deriving Capa-
bilities method is not yet automated. The user configures
the manufacturing work plan of the product via a GUI of
the service requester.
It is still unclear how a method for capability matching
and the feasibility check can be realized concretely. So
far, only required and provided capabilities and skills
have been considered as input information, but the
properties of the workpiece must also be taken into
account. The example of drilling makes it clear that
product properties such as weight, dimensions or mate-
rial are an indispensable part of the feasibility check.
However, it is still unclear how this can be methodically
implemented.
Figure 13: PaaS demonstrator of the OvGU


# 2025-i40-capabilities (1)

## Seite 29

29
3.5.3 Technology Mapping
The interactions between service requester and service
provider are defined by the I4.0 language according to
VDI 2193. This language specifies both the message
structure and interaction protocols for certain use cases,
such as bidding. The specification leaves open which
means of communication is used to transmit the mes -
sages. For pragmatic reasons, MQTT was chosen. The
service description, which is part of the I4.0 message, is
modelled on the request and assurance side as a custom
AAS submodel that integrates both technical and com-
mercial aspects. The technical aspect is soon to be
replaced by the Capability Description Submodel of the
IDTA, which is currently still under development 10. A
standardized service submodel is also preferable in
terms of this use case.
If the negotiation has led to an accepted offer, the ser -
vice provider provides the service by executing a corre-
sponding skill via an OPC UA skill interface. The skill is
mapped in PackML according to ISA88 and ultimately
implemented on a PLC using OPC UA, extended by the
Companion Specification ‘OPC 30050 PackML’ .
However, the functions of the machines used are severely
limited, meaning that they cannot be used for real pro-
duction purposes. On the one hand, this means that the
skill is modelled in a simplified way due to a low number
of parameters and, on the other, that there is no map-
ping of capability properties to the respective skill
parameters.
10 https:/ /industrialdigitaltwin.org/en/content-hub/submodels
3.5.4 Outlining CSS Model Extensions
This use case shows the full range of the CSS model,
from negotiating services to matching at capability level
and executing skills. The interactions between service
requester and service provider require a common seman-
tic understanding of the services and capabilities to be
negotiated. It should be taken into account that the
capabilities should be modelled from different perspec-
tives in order to enable matching procedures. A capabil-
ity description from the service requester's perspective
formulates requirements for the required capability,
while the capability description from the service provid-
er's perspective contains assurances. The CSS model
currently lacks methods that lead to capability descrip-
tions from both perspectives. Furthermore, it is still
unclear how services can be restricted by constraints,
e.g. to filter for certain offer properties in a request.


# 2025-i40-capabilities (1)

## Seite 30

30
4 Revision and Refinement
of the CSS Model
After considering the previously presented methods and
use cases, the necessary model extensions were dis -
cussed and prioritized in the working group. The most
important ones were incorporated into a first revision of
the CSS model initially presented in [2].
The extensions are divided into three parts. First, Section
4.1 outlines a refinement regarding the Skill and Skill -
interface descriptions. Second, Section 4.2 analyzes the
state of the art and proposes a revision of how to
describe a Service using the Property class. Third, Section
4.3 refines the way in which capability and service con-
straints are modeled and introduces PropertyConstraints
and TransitionConstraints.
4.1 Refinement of Skill
An extension of the skill model is required to more pre-
cisely represent invocation details and ensure interoper-
ability between skills from different manufacturers, as
well as skills and execution applications such as MES.
The existing CSS model only specifies that a Skill may
have SkillParameters and that the behavior of a Skill is
described with a StateMachine. Furthermore, every Skill
must have at least one so-called SkillInterface, which
exposes access to the StateMachine and SkillParameters.
However, more precise details that show how a Skill-
Interface can be used to interact with a Skill are
lacking.
To be able to model these details more precisely, the
Skill aspect of the CSS model is extended. Figure 14
shows the extensions made to the Skill aspect. Newly
added classes are displayed in blue. To maintain read-
ability, this figure only shows the Skill aspect and all
directly related model elements. Classes for States and
Transitions are introduced, which can be used to describe
the structure of the StateMachine of a Skill. It was delib-
erately decided not to specify a particular state machine
(e.g., PackML [14], but to allow any state machine to be
represented using the two classes State and Transition.
From the perspective of a State, Transitions can be
incoming or outgoing. A State can take on the role of the
source or target of a Transition. Every Skill is associated
with its current State using the hasCurrentState
relation.
Figure 14: Model extensions to the skill aspect (added class in blue)


# 2025-i40-capabilities (1)

## Seite 31

31
A new class SkillTrigger is introduced to model a way of
interacting with the StateMachine’s transitions. A Skill-
Trigger is used to activate the Transition it’s related to. In
addition to Transitions that can be triggered externally
via a SkillTrigger, there can also be Transitions that are
triggered by the internal logic of the StateMachine. From
a technical perspective, SkillTriggers may be imple-
mented in various ways, e.g., using method calls or writ-
ing variables in OPC UA. The details of technical imple-
mentations are not the subject of this white paper and
may instead be added in future extensions.
Just like the StateMachine and SkillParameters, SkillTrig-
gers are also exposed from a SkillInterface. In addition,
SkillTriggers may have SkillParameters. These can be
used in cases where a parameterization must be assured
before or during a Transition. Two corresponding sub-
classes of the existing SkillParameter class have also
been added to distinguish between input and output
parameters.
4.2 Revision of Service
In addition to the elements of the Skill and the Capabil-
ities, the Service element has also been refined. The Ser-
vice element outlines the commercial aspects and deliv-
ery methods of the offered Capabilities. It was included
in the previous model version and has not been altered
structurally. However, the assures relation left room for
interpretation. Furthermore, the specific Properties that
represent a Service in sufficient detail were vaguely
defined. This section aims to clarify those terms.
4.2.1 Element Relations
Relation between Service and Product
The name of the assures relation from the previous
model was ambiguous. Therefore, the relation was
renamed provides to express better that the Service puts
the manufactured Products into the possession of the
ServiceRequester for usage, consumption, or disposal.
4.2.2 Service Properties
We conducted an online review of service properties for
manufacturing. It revealed no universally accepted or
standardized properties for services, which are crucial
for negotiating services in an open, decentralized mar -
ketplace for manufacturing-as-a-service. Therefore, this
section presents collected commercial properties from
several guidelines for a shared understanding of poten-
tial manufacturing service properties.
However, there are no common guideline properties for
IT service contracts or manufacturing, which also poses
a challenge for the service definition of capabilities and
skills.
IT Service Contracts
The University of Cornell published a guideline [26] on
the IT service contracts for their university that suppliers
and providers need to adhere to.
EU Guideline on Public Procurement
Public procurement is key to the Europe 2020 strategy
as a market-based instrument for smart, sustainable,
and inclusive growth. Therefore, the public modernized
procurement rules were adopted to increase public
spending efficiency, facilitate the participation of Small
and Medium-Sized Enterprises (SMEs) in public pro-
curement, and enable procurers to better use public
procurement in support of common societal goals.
There is also a need to clarify basic notions and concepts
to ensure legal certainty and to incorporate certain
aspects of related well-established case-law of the
Court of Justice of the European Union. [27]
PAS 1018
PAS 1018 [18] is a Publicly Available Specification (PAS)
that describes the basic services structure within a pro-
curement process. This basic structure is a generic start-
ing point and can be flexibly extended to integrate
industry and company-specific requirements with little
effort. PAS 1018 focuses on the procurement steps prior
to the actual provision of services. These include require-
ments identification, description, cost estimation, mar -
ket analysis, selection of suitable suppliers, and tender -
ing. PAS 1018 provides the corresponding descriptive
criteria for these steps, shown in the table below. It is
important to note that PAS 1018 only focuses on the


# 2025-i40-capabilities (1)

## Seite 32

32
pre-service phases. Accordingly, it does not consider
phases during and after service provision. PAS 1018 is
still accessible but has been officially withdrawn.
In addition to the guidelines presented, the UN/EDI -
FACT (United Nations / Electronic Data Interchange for
Administration, Commerce and Transport) standard and
model contracts and clauses of the International Cham-
ber of Commerce (ICC) are not included in the table.
UN/EDIFACT is a cross-industry standard for electronic
data exchange in business transactions. However, the
standard relates primarily to the message structure for
data exchange and less to the definition of general ser -
vice properties11. Among other things, the ICC provides
model contracts and clauses that can be used, for exam-
ple, as templates for the trade in goods and services [28].
As the documents of ICC are not freely available, they
were not considered further. The following table offers
an overview of properties derived from guidelines and
the state of the art, serving as a practical reference and
proposal for stakeholders regarding service properties.
11 https:/ /unece.org/trade/uncefact/introducing-unedifact
Table 1: Summary of Properties
IT Service Contracts
Cornell
EU Guideline on
Public Procurement
PAS 1018 Description
Description of services Technical specification Service item  The scope of services, which may include identification
and classification; in the context of the CSS model, this is a
reference to capability.
Quality control Quality criteria, levels,
and control
Qualitative information Quality criteria that allow the evaluation of a service provi-
ded; in terms of the CSS model, it is conceivable to provide
a reference to part of the capability specification.
Warranties/insurance Insurance Warranties/insurance Describes the warranties, guarantees, liabilities and insu-
rance of the service
Completion date /
Timetable
Time scheduling, performance
period, contract duration
(milestones)
Includes the planning of a service, including the execution
period, defined milestones, and a completion date
Price Offer price of the principal,
specified price of the client
May include a negotiated or fixed price
Terms of payment Terms of delivery and payment Describes the general terms and conditions under which a
delivery or payment is made
Scalability Quantity of the service, Unit of
the service, Frequency
Contains the quantitative information about the service;
this can be factors such as quantity, unit or frequency.
Intellectual property
rights (IPR)
Intellectual property
rights
Describes legal protections that give individuals or compa-
nies exclusive performance and control over a service
Indemnification Indemnification Defines the consequences of not providing a service
Termination and
cancellation
Describes the conditions under which it is permissible not
to provide a service


# 2025-i40-capabilities (1)

## Seite 33

33
Confidentiality and
non-disclosure
All material shall be utilized by Service Provider solely in
connection with the performance of the Services under
this Agreement [26].
Governing law Describes compliance with national laws in negotiations
within the EU or at global level
Force majeure Unforeseeable circumstances that may prevent one or
both parties from fulfilling their obligations.
environmental and cli-
mate performance
levels
Describes the assessment of the expected environmental
impact, e.g. the CO2 footprint
Offer binding period (under
other agreements in PAS1018)
Indicates the length of time for which an offer is legally
valid
Prequalification (information
required from the supplier and
reference to internal supplier
evaluation)
May include certificates, economic performance, technical
performance, approvals
Place of provision Describes the location where the service is provided
4.3 Constraints of Capabilities
and Services
During refinement of the CSS model, the class Capabili-
tyConstraint, which was already included in the previous
version of the model, was renamed to Constraint and
extended by two more specific subclasses of constraints.
These two subclasses differ in terms of their relationship
to other model elements and are defined in the follow-
ing two subsections.
4.3.1 PropertyConstraint
A PropertyConstraint is a constraint that determines the
applicability of a Capability and that refers to one or
more Properties of the same Capability (see Figure 15).
An important aspect of PropertyConstraints is that they
always refer to a single Capability and assume no knowl-
edge of a sequence of Capabilities or dependencies
between Capabilities.
For this type of constraint, expressions can be made
between
• properties and constant values (e.g. product.width <=
100 mm), or
• one or more properties (e.g. product.width <= work -
space.width).
In terms of their temporal link to an application of a
Capability, PropertyConstraints can be divided into:
• Preconditions: Constraints that must hold before a
Capability can be applied
• Invariants: Constraints that must hold during applica-
tion of a Capability
• Postconditions: Constraints that must hold after a
Capability has been applied
A PropertyConstraint can arise from a wide variety of
requirements:
• Legal regulations: Certain countries might exclude other
countries as production locations. This can be expressed
as a machines.location != “within other's country border” .
• Budget restrictions: In a CNC milling process, keeping
the precision of a feature at the maximum tolerable,
makes an additional milling step with a more precise
tool superfluous, e.g. feature.tolerance >= 1 mm.
• Physical limitations: In a tempering process including
water in a non-pressured environment the temperature
must be kept below a threshold to prevent the loss of
water in the form of steam, e.g. temperature.max = 95°C.
• Technical requirements: In a CNC milling process the
used tool might break/crack if the process speed is very
high, thus a maximum speed is needed to restrict the
tool from breaking, e.g. process.tool.speed <= 10mm/s.


# 2025-i40-capabilities (1)

## Seite 34

34
4.3.2 TransitionConstraint
A TransitionConstraint is an expression between multiple
Capabilities or Services, determining the applicability of
a Capability or Service in a wider context. In a Transition-
Constraint, a dependent Capability or Service is restricted
by one or more referenced Capabilities or Services. Tran-
sitionConstraints can be used to formulate requirements
going beyond PropertyConstraints, especially sequence
requirements.
In terms of their temporal link to an application of a
Capability, TransitionConstraint conditions can be
divided into:
• Preconditions express a situation in which referenced
Capabilities must be applied before the restricted
Capability can be applied. Example: Ramp-up, Transport
• Invariant conditions must hold during application of a
Capability, i.e., referenced Capabilities must be applied
in parallel with the dependent one. Example: Supply-
ing of lubricant during milling
• Postconditions are used where referenced Capabilities
must be applied after the dependent Capability has
been applied. Example: Clean-up, Transport
In contrast to PropertyConstraints, TransitionConstraints
cannot be evaluated for a single Capability alone.
Instead, they must always be considered with respect to
a sequence of Capabilities.
Figure 16: Newly added class TransitionConstraint, the renamed class Constraint and its relations to neighboring model elements
Figure 15: Newly added class PropertyConstraint, the renamed class Constraint and its relations to neighboring model elements


# 2025-i40-capabilities (1)

## Seite 35

35
4.4 Revised CSS Model
After the explanation and introduction of a first revision
of the CSS model, Figure 17 visualizes version 2 of the
CSS model. The basic structure regarding the subdivision
into Service, Capability, Skill and PPR remains in place.
The Skill is extended in accordance with Section 4.1.
Extensions are the classes State and Transition, which
are intended to describe the structure of the StateMa-
chine of a Skill in more detail. A SkillTrigger determines
how to activate a Transition. In order to recognize which
SkillParameters must be set when a Skill is called and
which parameters can be read after completion, param-
eters are further subdivided into InputParameter and
OutputParameter.
With regard to Capability, the previously used Capabili-
tyContraints has been removed, and a generic class Con-
straint has been introduced in the PPR part. The generic
constraints are divided into PropertyConstraints and
TransitionConstraints, and can be used for Capabilities
and Services. In this context, Capabilities and Services
have dependencies on the introduced PropertyCon-
straints and TransitionConstraints (see Section 4.3).
Section 4.2.2 is a collection of attributes that can be
used for the Service description. At this point, explicit
attribution in the CSS model has been omitted. The rea-
sons for this are the consistency of the CSS model (attri-
butes should be used for all classes) and the fact that an
implementation-independent model should not be
restricted and limited by attribution.
Figure 17: Revised CSS model (added class and relations in blue)


# 2025-i40-capabilities (1)

## Seite 36

36
5 Conclusion and Outlook
Facing rapidly evolving environments in manufacturing
requires flexibility in production. Using the CSS model as
a means to implement capability-based engineering
enables the decoupling of product design from produc -
tion planning and execution. This contribution provides
methods for the formal description of capabilities, their
assignment to resources, and their derivation from
product specifications or process descriptions.
The method Capability Determining proposes a struc -
ture to encompass the description, assignment and der-
ivation of capabilities. This technology-independent
method helps stakeholders to navigate the complexities
of capability-based engineering. With the developed
methods to describing, assigning and deriving capabili-
ties, the CSS model is getting more manageable for
developers in industrial areas. The method Describing
Capabilities shows how to formalize capabilities with
their semantic symbol, properties and constraints, using
existing standards. In Assigning Capabilities, the
resources are identified with their skills as well as the
effect of the skills. On this basis, the offered capabilities
are assigned to the resources. The third method Deriving
Capabilities includes the derivation of required capabili-
ties from product or process descriptions. Over all three
methods, a main method Determining Capabilities was
introduced to describe the flow between them. Future
work needs to thoroughly check the developed methods
and to add improvements.
Furthermore, similar methodologies should be devel-
oped for skills and services. This paper introduces the
methods Determining Capabilities with their sub-meth-
ods. Their principle approach and these methods them-
selves can serve as a starting point for developing meth-
ods for skills and services definitions. It could be that the
CSS model, in particular the skill has to be extended by
constraints similar to those of the capability. Especially,
defining services for capabilities and skills poses a chal-
lenge because there are no common guideline proper -
ties for IT service contracts or in manufacturing. For this,
future research work is necessary.
Additionally, the paper summarized different use cases
from the process industry as well as manufacturing
where the CSS model has been transferred to the real
world. The integration work revealed some gaps, leading
to a new extended CSS model, which is presented above.
However, further research is still necessary: Among
other things it needs to be established, how to parame-
trize, execute and interpret the behavior of skills or how
to connect capabilities and services on different levels of
abstraction. In addition, already existing formal capabil-
ity descriptions need to be merged and refined.
Our research identifies topics, which has to be validated
by the working group “Semantik und Interaktion von
I4.0-Komponenten” of Plattform Industrie 4.0. A pilot
implementation for the interaction with the CSS model
as well as the validation of the methods is currently
under development. Therefore, tool support is needed,
also to involve various stakeholders. In addition to the
current capability concept, the concept of effects has
been identified and partially included into the methods.
The concept of effects of manufacturing functions is
published in [12]. Furthermore, it should be mentioned
that all described use cases used different technologies
for the technical implementation, which are not
explained in detail. This may be added in future exten-
sions of the CSS model papers to help developers. Fur -
thermore, a major goal is to link the work of the single
use cases into a general network called CSS+ pilot to
demonstrate the interoperability of the CSS model. For
this purpose, working groups have been formed and
have started their work. In the context of the further
development of the methods for Determining capabili-
ties, the sufficiency check of existing capability descrip-
tions needs to be elaborated. E.g. parameters need to be
specified to quantify the sufficiency of a capability
description. Further, a method specification for the suf -
ficiency check has to be developed.


# 2025-i40-capabilities (1)

## Seite 37

37
Annex A – Changes in the CSS model
This annex lists the changes from one version to other
versions of the model in Table 2. Non-backward com-
patible changes (nc) are marked as such.
nc="x" means non-backward compatible; if no value is
added in the table, then the change is backward
compatible.
nc="(x)" means that the change made was implicitly con-
tained or stated in the document before and is now
being formalized. Therefore, the change is considered to
be backward compatible.
Annex B - Stakeholder Personas
The following pages list different stakeholders, who are
able to apply the methodology described in this paper in
their day-to-day work. The personas serve as reference
points for the later development of the methods. Some
of the personas developed at the beginning of the work
were redeveloped with regard to the tasks that arise
with the CSS model, e.g. a capability modeler. Every
stakeholder description is divided into information
about the personal motivation and the goals of the
stakeholder, as well as into gains and pains of the daily
work.
The portraits of the stakeholder are generated by Adobe
Firefly.
Table 2: Changelog to CSS model
nc CSS+ model changes w.r.t CSS
model
Comment
State New element, see Section 4.1
Transition New element, see Section 4.1
consistsOfState Specifies number of States of a state machine, see Section 4.1
consistsOfTransition Specifies number of States of a state machine, see Section 4.1
target - incoming Links a target State with incoming Transitions, see Section 4.1
source - outgoing Links a target State with incoming Transitions, see Section 4.1
hasCurrentState Specifies actual State of a state machine, see Section 4.1
SkillTrigger New element to activate a Transition through an interface, see Section 4.1
hasTrigger Associates that a SkillInterface has a SkillTrigger, see Section 4.1
isInvokedBy Links a Transition with the respected SkillTrigger, see Section 4.1
expose Associates that a Skill may have a trigger to control the state machine, see Section 4.1
OutputParameter New element to emphasize for parameters to read after skill execution, see Section 4.1
InputParameter New element to emphasize for parameters to set before skill execution, see Section 4.1
hasParameter Describes that SkillTrigger needs SkillParameters before the Transition can be invoked, see Section 4.1
X CapabilityConstraint
-> Constraint
Renamed as more elements can be restricted (isRestrictedBy), e.g. Service, see Section 4.2
isRestricedBy Can restrict Service and Capability
PropertyConstraint New element, see Section 4.3.1
TransitionConstraint New element, see Section 4.3.2
X references -> referencesProperty Renamed to reflect the purpose of the relationship
Added Methods Methods for Determining Capabilities including Describing, Assigning and Deriving Capabilities
Change Relation Relation between Service and Product has changed from assures to provides


# 2025-i40-capabilities (1)

## Seite 38

38
Maria Schmied
Maria Schmied is an experienced sales manager who specializes in the sale of technical
resources with special capabilities. She works closely with product management to ensure
that the capabilities offered meet the requirements and wishes of customers. Julia is
always keen to understand the needs of her clients and offers customized solutions to
overcome their specific challenges. She uses her deep understanding of the technical
aspects of the products to communicate effectively with customers and the internal team,
always aiming for high customer satisfaction and increased sales.
Age: 38
Gender: Female
Education: Master's degree
in business administration
Profession: Sales Manager
Gain
• Clear and comprehensible product descriptions
that enable targeted marketing
• Effective and efficient customer service to improve
customer loyalty and satisfaction
• Using customer feedback to continuously improve
the offering
Pain/Frustration
• Competitive pressure and price wars that lead to
reduced margins
• Complex technical documentation that makes
 communication with non-technical customers difficult
• Customer concerns about the appropriateness of the
price and the quality of the capabilities
Goals
• Increasing turnover by increasing sales figures and
achieving sales targets
• Acquiring and retaining customers through
customized solutions
• Expanding the range with market-driven capabilities
Character
• Determined and results-oriented
• Excellent communication skills
• Strong problem-solving skills
• Ability to understand and explain complex
products and services


# 2025-i40-capabilities (1)

## Seite 39

39
Thomas Berger
Thomas Berger is responsible for the planning, organization and monitoring of production
processes in a manufacturing company. His main tasks include managing resources, opti-
mizing workflows and ensuring that production targets are met. In doing so, he relies on
the use of modern capabilities to optimize the production flow and increase efficiency.
The production planner works closely with various departments to ensure that products
meet quality standards and are delivered on time. He is a crucial factor in the supply chain
and plays a central role in the company's ability to respond to market requirements.
Age: 45
Gender: Male
Education: Master's
degree in mechanical
engineering
Profession:
Production planner
Professional experience:
20 years in the
manufacturing industry
Gain
• Clear and precise capability assignments to avoid
errors
• Better foresight and planning for resource availability
• Flexibility in dealing with short-term changes in
production
• Integration and easy use of standardized capabilities
Pain/Frustration
• Misallocation of capabilities leading to production
errors
• Bottlenecks and resource shortages that disrupt the
production flow
• High complexity in the management of different
product variants
• Pressure to reduce costs without compromising quality
Goals
• Ensuring efficient and error-free production processes
• Reducing costs by optimizing the use of resources
and minimizing material waste
• Quality assurance and meeting delivery deadlines
• Reacting quickly to market changes and customer
requirements
Character
• Detail-oriented and methodical
• Problem solver with a preference for structured
approaches
• Communicative and team-oriented
• Adaptable to technological changes


# 2025-i40-capabilities (1)

## Seite 40

40
David Müller
David Müller is an experienced software developer specializing in the development and
integration of software capabilities. He strives to improve software quality and optimize
development processes through effective modeling and clear communication. His focus is
on creating cross-platform models and implementing capabilities that are both functional
and compatible with existing systems.
Age: 32
Gender: Male
Education: Master in
computer science
Profession: Software
developer in the field of
capability modeling
Professional experience:
8 years in software devel-
opment, specialized in
system integration and
capability modeling
Gain
• Access to improved and more up-to-date technical
documentation
• Greater standardization of data models and interfaces
• Development tools that make it easier to set up and
configure development processes
Pain/Frustration
• Insufficient documentation and technical
specifications that slow down the modeling process
• Lack of standardization, which makes code reusability
difficult
• Frequent misunderstandings and communication
gaps between developers and other stakeholders
Goals
• Development of cross-platform models and interfaces
• Quality improvement of the software through
systematic capability descriptions
• Efficient communication and coordination between
different development teams
Character
• Detail-oriented and analytical
• Prefers clear structures and organized ways of working
• Patient and methodical in solving complex problems
• Team-oriented, but also able to work independently


# 2025-i40-capabilities (1)

## Seite 41

41
Julia Meier
Julia Meier is an experienced software developer who specializes in the development of
software modules for industrial automation systems. She works efficiently in the various
phases of software development, from planning to use. Julia is particularly adept at trans-
forming abstract capability descriptions into concrete, robust software solutions. Her
motivation is to make software development more efficient and error-resistant by improv-
ing communication and documentation between the teams involved.
Age: 28
Gender: Female
Education: Master
in computer science,
specialization in
software engineering
Profession: Software
developer regarding skill,
resource and process
(Programmable Logic
Controller (PLC)
developer, skill developer,
Software interfaces to
skills, ...)
Professional experience:
Senior software developer,
specialized in industrial
automation
Gain
• Access to advanced development tools that support
automated software development and improve error
detection
• More opportunities for further training in the latest
software engineering technologies and methods
Pain/Frustration
• Incomplete or incorrect technical documentation,
which delays development
• Lack of communication between departments,
leading to duplication of work
• Software errors due to misunderstandings in the
capability description, poor integration testing
Goals
• Short-term: Improving capability modeling for the
smooth integration of new software modules into
existing systems
• Long-term: Leading a development team that redefi-
nes the standards in industrial software development
Character
• Working method: Structured, detail-oriented,
innovative problem-solving
• Interaction style: Clear communicator,
team-oriented, leader
• Strengths: Technical expertise, quick comprehension,
ability to abstract and model complex systems


# 2025-i40-capabilities (1)

## Seite 42

42
Claudia Richter
Claudia Richter works as a system integrator in factory automation. She is responsible for
the seamless integration of software and hardware components in factory systems. Her
daily work includes the planning, definition, design and realization of system integrations
based on specific customer requirements. Claudia uses capability catalogs from compo-
nent and software manufacturers to identify and implement suitable solutions. She is par-
ticularly keen to develop a customized solution that is precise and efficient. Her biggest
frustration is insufficient data in the capability catalogs, which can slow down her work.
Age: 37
Gender: Female
Education: Master's degree in
electrical engineering
Profession: Systems integrator
in factory automation
Gain
• Access to comprehensive and up-to-date
capability catalogs
• Better automation of system integration to
save time and reduce errors
• Increased flexibility in adapting systems to
customer-specific requirements
Pain/Frustration
• Incomplete or missing information in capability
catalogs
• Capabilities not available that are needed for
specific customer requirements
• Delays in the procurement or integration of
components
Goals
• Efficient and error-free integration of software and
hardware into existing or new factory systems
• Guarantee the compatibility and functionality of all
system components
• Quick adaptation to new technologies and methods
Character
• Detail-oriented, analytical, problem-solving,
communicative
• Methodical and structured, prefers clear and precise
information
• Cooperative, prefers direct communication


# 2025-i40-capabilities (1)

## Seite 43

43
Thomas Mayer
Thomas Mayer is an experienced simulation engineer who specializes in the simulation of
production processes. His main task is to ensure that the capabilities defined in the design
phases are practical and effective. He uses advanced simulation software to test and vali-
date the processes before implementation. Thomas strives to improve the quality and reli-
ability of products through his work. However, he often faces challenges such as insuffi-
cient data or time constraints that affect his ability to perform thorough and accurate
simulations.
Age: 35
Gender: Male
Education: Degree in
mechanical engineering
Profession: Simulation techni-
cian in process simulation
Gain
• Access to improved simulation software and tools
• More time for thorough testing and validation
• Better collaboration and information sharing with
other departments
Pain/Frustration
• Insufficient or incorrect data, which affects the
accuracy of the simulations
• Time pressure, which often leads to compromises in
the quality of simulations
• Lack of advanced tools and technologies that could
improve simulation results
Goals
• Ensuring that all proposed capabilities can be cor-
rectly implemented and validated through simulation
processes
• Improving efficiency and accuracy in the simulation
tests
• Early detection and elimination of problems in the
development phase
Character
• Accurate, methodical, critical, innovative
• Systematic, with a strong focus on accuracy and
validity
• Enjoys working in a team, but can also solve complex
problems independently


# 2025-i40-capabilities (1)

## Seite 44

44
Julia Schneider
Julia Schneider is a dedicated electrical engineer who specializes in the integration and
optimization of electrical engineering systems through the use of capabilities. She uses
her technical expertise and communication skills to develop and implement innovative
solutions that improve both the efficiency and effectiveness of electrical engineering proj-
ects. Julia's goal is to promote the use of capabilities in the electrical engineering field and
to convince her colleagues and the industry of their benefits.
Age: 31
Gender: Female
Education: Bachelor in
electrical engineering
Profession:
Electrical engineer
Professional experience:
8 years, specialized in elec-
trical engineering planning
and capability modeling
Gain
• Access to more detailed and specific technical docu-
mentation for a better understanding of capabilities
• Greater support for management and colleagues in
the implementation of capabilities
• Training opportunities in advanced capability
modeling and application
Pain/Frustration
• Lack of specifications and unclear requirements for
the integration of capabilities
• Resistance within the team to new technologies and
methods
• Difficulties in convincing stakeholders of the benefits
of capability-based approaches
Goals
• Integration of offered capabilities in electrotechnical
plans
• Optimization of electrotechnical systems through
innovative use of capabilities
• Promoting the understanding and application of
capabilities in their field of work
Character
• Solution-oriented and creative
• Strong focus on efficiency and practicability
• Highly adaptable and willing to learn
• Communicative, with a tendency to encourage active
teamwork


# 2025-i40-capabilities (1)

## Seite 45

45
Markus Weber
Markus Weber is a highly qualified design engineer with over 20 years of professional
experience in machine design. He specializes in the development of machines that offer
both specific and broad capabilities. Markus works closely with other teams to ensure that
the machines he develops meet the latest standards and operate efficiently. His profound
understanding of technical documentation and his ability to turn requirements into inno-
vative designs make him an indispensable member of his company. Markus strives to stay
at the forefront of technological developments and continuously improve his designs to
meet the changing demands of the market.
Age: 46
Gender: Male
Education: Degree in
mechanical engineering
Profession:
Machine design engineer
Professional experience:
20 years, specialized in
machine design
Gain
• More resources for research and development of new
technologies
• More collaboration with other departments to
develop interdisciplinary solutions
• Better tools and software for the design and
simulation of machine constructions
Pain/Frustration
• Frustration due to limitations caused by existing
technical possibilities and budget restrictions
• Difficulties in integrating new technologies into
traditional design concepts
• Challenges due to frequently changing requirements
and objectives in projects
Goals
• Development of machines that offer specific capabili-
ties optimally
• Designing machines that are versatile and support a
wide range of capabilities
• Continuous development of in-house technical skills
and knowledge of the latest technology
Character
• Creative, innovative, precise, solution-oriented
• Places great value on detailed planning and precise
execution; prefers clear, functional designs that
maximize technical efficiency


# 2025-i40-capabilities (1)

## Seite 46

46
Claudia Meier
Claudia Meier is an experienced engineer who has been working in product development
for over 20 years. She is currently working on optimizing production processes to achieve
higher quality standards while reducing costs. Claudia is particularly interested in intro-
ducing new technologies and improving sustainability in production. Her main tasks
include the planning and implementation of project planning phases, the application of
the CSS model to optimize capability utilization and the development of measures for
quality control and cost reduction. Her in-depth technical knowledge and leadership skills
make her a key person in her company.
Age: 48
Gender: Female
Education: Master's
degree in mechanical
engineering
Profession:
Senior engineer in
product development
Professional experience:
20 years specialized in
production process
optimization
Gain
• Desire for greater integration of digital technologies
and automation in production processes
• Efforts to implement a more effective quality control
system
• Desire for more efficient and environmentally friendly
production
Pain/Frustration
• Frustration over repeated production bottlenecks and
quality problems
• Challenges in dealing with fluctuating material
qualities and delivery times
• Difficulties in keeping pace with technological
innovations and Industrie 4.0
Goals
• Increasing product quality and efficiency in
production
• Reducing production costs through optimized
processes and use of materials
• Developing innovative products while taking
sustainability aspects into account
Character
• Analytical, detail-oriented, decisive, adaptable
•  Structured and goal-oriented, prefers data-based
decision-making


# 2025-i40-capabilities (1)

## Seite 47

47
Lukas Schuster
Lukas Schuster is an experienced product designer with a master's degree in mechanical
engineering and 10 years of professional experience. He is known for his creativity and
attention to detail, which help him develop innovative and competitive products. He
works systematically and analytically, constantly striving to improve the efficiency of
design processes and reduce time-to-market. Lukas sees the integration of versatile and
specialized capabilities as key to creating products that meet current market trends and
customer requirements. Despite the challenges related to resources and the acceptance of
new technologies, he remains motivated to create high-quality and reliable products that
stand out from the competition through the use of these capabilities.
Age: 35
Gender: Male
Education: Master's
degree in mechanical
engineering
Profession: Product
designer (engineer)
10 years, specialized in
efficient product design
Gain
• Using capabilities to develop innovative and unique
solutions
• Improving product quality and reliability through
targeted integration of capabilities
• More efficient design processes through reusable
components and technologies
• Increasing customer satisfaction by meeting specific
requirements and expectations
Pain/Frustration
• Difficulties in integrating new capabilities into
existing product architectures
• Limited resources and cost constraints
• Challenges in ensuring the reliability and quality of
new capabilities
• Resistance or concerns from customers regarding
new or unfamiliar capabilities
Goals
• Creating innovative and competitive products by
integrating versatile and specialized capabilities
• Adapting products to current market needs and trends
• Optimizing design processes and reducing
time-to-market
Character
• Creative, detail-oriented, technically skilled,
team player
• Systematic, analytical, proactive
• Clear, precise, cooperative


# 2025-i40-capabilities (1)

## Seite 48

48
Karl Bauer
Karl Bauer is an experienced resource provider. He offers various resources through digi-
tal catalogs and platforms, aiming to keep these resources continuously utilized. Karl
strives to expand and innovate his resources according to market demands. He places
great emphasis on the safety, quality, and profitability of his resources while meeting the
high expectations of his customers. His strategic thinking and proactive actions enable
him to build a broad and satisfactory customer portfolio.
Age: 45
Gender: Male
Education: Master's degree in
mechanical engineering
Profession: Resource provider
Gain
• Access to detailed technical documentation,
data sheets, and relevant standards
• Ability to define unique capabilities and bring new
innovations to the market
• Flexibility in the customization and modification of
resources
• High quality and reliability of offered resources,
compliance with safety standards
Pain/Frustration
• Machines should be continuously utilized;
idle times lead to revenue losses
• Regular maintenance is necessary but
time-consuming
• Resources must comply with current safety regulations
• High costs for acquisition, maintenance, and
operation of resources while ensuring competitive
advantages and profit margins
• High expectations and requirements of customers
must always be met
Goals
• Maximizing resource utilization and reduce idle times
• Building a broad and standardized customer portfolio
to secure sustainable revenue streams and expand
the business
Character
• Analytical, detail-oriented, solution-oriented,
strategic thinker
• Proactive, reliable, innovative
• Interested in technology, market research, networking


# 2025-i40-capabilities (1)

## Seite 49

49
Sarah Johnson
Sarah Johnson has 10 years of experience in procurement. She is well-versed in the chal-
lenges of sourcing parts. Her goal is to make the procurement process more efficient and
reduce costs. Sarah values structured and proactive work methods to achieve her goals.
She experiences frustration due to inconsistent descriptions and time-consuming com-
parisons of components. Her wish is for a unified and easily accessible database that
enables quick and accurate selection.
Age: 34
Gender: Female
Education:
Bachelor's degree in
business administration
Profession:
Procurement specialist
Professional experience:
10 years, specialized in
sourcing parts
Gain
• Consistent and easily comparable descriptions of
parts across different manufacturers
• Faster discovery of components through a capability
match with catalogs or platforms
• Read-only access to requirements and offers to make
informed decisions
Pain/Frustration
• Difficulties in finding suitable parts
• Time-consuming comparisons of components due to
inconsistent descriptions
• Limited access to essential requirement documents
and offers
Goals
• Quick and efficient procurement of required parts
• Optimization of procurement processes, cost reduc-
tion, building stable supplier relationships
Character
• Detail-oriented, analytical, strong negotiator, reliable
• Structured, proactive, team-oriented
• Clear, precise, diplomatic communication skills


# 2025-i40-capabilities (1)

## Seite 50

50
Emily Fisher
Emily Fisher is an experienced production planner known for her analytical skills and
attention to detail. She is responsible for planning and organizing production orders,
resource utilization, and schedules. Her main goals are optimizing production processes,
ensuring product quality, and meeting customer demands. Emily is often frustrated by the
complexity of production processes and bottlenecks, but continually strives for efficiency
improvements and smooth production. Her wishes include better resource utilization and
higher system interoperability to avoid errors and ensure consistent planning results.
Age: 50
Gender: Female
Education: Master's degree in
mechanical engineering
Profession: Production planner
Gain
• More efficient use of existing resources through
accurate capability assignment
• Reduction of complexity in production planning
through standardized processes
• Improved interoperability between different systems
and departments
• Avoidance of errors and inconsistencies through con-
sistent capability modeling
• Flexibility in resource allocation and switching during
production
Pain/Frustration
• Incorrect capability assignment leading to defective
products
• Complexity of production processes due to variety
and customer-specific requirements
• Bottlenecks and resource shortages
(machine capacity, skilled labor, material availability)
• Last-minute changes or prioritization of orders
• Pressure to optimize costs and efficiency without
compromising quality and deadlines
Goals
• Smooth processing of current orders with optimal
resource usage
• Optimization of production processes in terms of
time and cost
• Increasing production capacity and efficiency, mini-
mizing material waste, ensuring quality and timely
delivery
Character
• Strong communication, assertive, stress-resistant
• Analytical, detail-oriented, solution-focused
• Structured, proactive, team-oriented


# 2025-i40-capabilities (1)

## Seite 51

51
Dennis Weber
Dennis Weber is an experienced financial controller in the manufacturing industry. With
an analytical and methodical approach, he strives to continuously improve his company's
cost structures. His main tasks include cost controlling, identifying the most cost-effective
resources, and creating business cases for investments. Dennis is the economic conscience
of his company and provides well-founded recommendations to optimize investment
costs and present alternatives. His goal is to increase the company's resilience against pro-
duction downtimes and ensure efficient use of resources.
Age: 45
Gender: Male
Education: Degree in business
administration (BWL)
Profession: Financial controller
Gain
• Continuous improvement of the company's cost
structure
• Identifying and utilizing the most cost-effective
resources
• Ensuring the amortization and economic viability of
investments
• Increasing resilience against production downtime
Pain/Frustration
• Inaccurate or outdated financial data, which can
hinder the analysis and decision-making process
• Navigating the complexities of industry regulations
and compliance requirements, which can be
time-consuming and challenging
• Dealing with unpredictable market conditions or
economic downturns that impact cost structures and
financial planning
Goals
• Create and maintain comprehensive business cases
for investments
• Develop strategies to optimize resource allocation
and minimize waste
• Contribute to the company's strategic planning by
providing well-founded financial recommendations
Character
• Analytical, detail-oriented, methodical
• Precise, thorough, structured work style
• Clear, direct, fact-based communication
• Data-driven, risk-aware, value-oriented
decision-making


# 2025-i40-capabilities (1)

## Seite 52

52
Erik Schneider
Erik Schneider is envisioned as a pioneer in the role of capability modeler within the IT and
manufacturing industries. With a strong background in systems integration and emerging
expertise in capability modeling, Erik is poised to lead the future integration of capabili-
ties into production systems. His visionary and analytical approach drives him to enhance
the flexibility and efficiency of production processes through advanced capability descrip-
tions. Erik is committed to establishing industry-wide standards and developing cut-
ting-edge tools to support capability modeling. He aims to overcome technological gaps
and organizational resistance by promoting collaboration and education within the indus-
try. Erik's future role focuses on leveraging capabilities to facilitate higher levels of auto-
mation, interoperability, and optimization in manufacturing, paving the way for more
adaptive and efficient production methods.
Age: 40
Gender: Male
Education: Degree in com-
puter science or related field
Profession:
Future capability modeler
Gain
• Development and adoption of standards and
advanced tools for capability modeling
• Increased collaboration among stakeholders to share
knowledge and best practices
• Expansion of training programs and creation of scalable
solutions for easy integration into production systems
Pain/Frustration
• Lack of mature technologies and standards for
capability modeling, limiting integration
• Difficulty persuading organizations to adopt new
methodologies and tools, with resistance to innovation
• Scarcity of expertise for developing precise models,
limited to pilot projects and research
Goals
• Leading the integration of capabilities and drive the
adoption of industry-wide standards
• Innovating to optimize production processes and
significantly increase automation
• Ensuring seamless integration and interoperability
between diverse systems and production units
Character
• Visionary, analytical, innovative
• Forward-thinking, structured, methodical work style
• Clear, persuasive, technically proficient communication
• Data-driven, strategic, solution-oriented decision-
making


# 2025-i40-capabilities (1)

## Seite 53

53
Lisa Müller
Lisa Müller is envisioned as a pioneer in the future role of capability manager within the
IT and manufacturing industries. With a strong background in database management and
data integration, Lisa is set to lead the establishment of standards for capability data
integrity and security. Her visionary and analytical approach drives her to optimize data-
base performance and spearhead standardization and integration efforts. Lisa is proactive
in implementing advanced validation mechanisms, comprehensive backup strategies, and
robust security measures. Her future role involves close collaboration with developers and
modelers to create efficient database models that support capability storage and retrieval,
ultimately enhancing decision-making processes and supporting business operations.
Age: 38
Gender: Female
Education: Degree in informa-
tion systems or related field
Profession:
Future capability manager
Gain
• Implementing mechanisms to enforce data integrity
and prevent inconsistencies
• Establishing comprehensive strategies to restore
capabilities in case of failures or data loss
• Deploying access controls, encryption, auditing, and
monitoring for data protection and compliance
Pain/Frustration
• Data inconsistency and data corruption,
leading to potential loss of critical information
• Ensuring that all users adhere to security policies
and practices
• Developing and maintaining comprehensive backup
strategies that minimize downtime and data loss
Goals
• Ensuring database capabilities are accurate,
consistent, and secure from unauthorized access
• Maintaining efficient database performance by
addressing bottlenecks and issues
• Standardizing capability descriptions and integrate
data across systems and platforms
Character
• Visionary, detail-oriented, responsible
• Structured, thorough, analytical work style
• Clear, direct, technically proficient communication
• Data-driven, strategic, cautious decision-making


# 2025-i40-capabilities (1)

## Seite 54

54
Maria Schehl
Maria Schehl is an experienced process specialist in the manufacturing technology industry,
known for her analytical skills and proactive approach. With a background in iIndustrial engi-
neering and extensive experience in process optimization, Maria focuses on deriving neces-
sary capabilities for specific technologies and production processes. She supports the devel-
opment of effective production planning and control methods by defining required
capabilities and providing detailed process-specific requirements for capability descriptions,
including constraints. Maria faces challenges related to complex capability requirements,
integration issues, and communication gaps. She aims to overcome these by leveraging
advanced tools, seeking seamless integration methods, and enhancing communication prac-
tices. Maria's role is crucial in ensuring that capabilities are accurately defined and effectively
integrated into production processes, thereby enhancing overall efficiency and performance.
Age: 52
Gender: Female
Education: Degree in
industrial engineering or
related field
Profession:
Future process specialist
Gain
• Access to tools that aid in accurately defining and
deriving capabilities
• Improved methods for integrating capabilities into
production systems
• Better communication channels and documentation
practices for clarity and alignment
Pain/Frustration
• Difficulty in defining and deriving capabilities for
diverse production technologies
• Issues integrating new capabilities into existing
systems
• Misunderstandings or lack of clarity in communicating
process requirements
Goals
• Identify and derive necessary capabilities for
technologies and processes.
• Assist in developing production planning and control
methods.
• Provide detailed requirements for capability
descriptions, including constraints.
Character
• Analytical, detail-oriented, proactive
• Methodical, precise, collaborative work style
• Clear, direct, technically proficient communication
• Data-driven, strategic, focused on process efficiency
decision-making


# 2025-i40-capabilities (1)

## Seite 55

55
Frank Schmidt
Frank Schmidt is an experienced application specialist in the manufacturing technology
industry, known for his problem-solving skills and innovative approach. With a back -
ground in automation engineering and extensive experience in application development,
he specializes in implementing skills that translate machine capabilities into functional
applications for product manufacturing. Frank faces challenges related to complex skill
requirements, tool limitations, and integration issues. He aims to overcome these by lever-
aging advanced tools, seeking better integration support, and pursuing continuous learn-
ing opportunities. Frank's role is crucial in ensuring that capabilities are effectively imple-
mented as practical and efficient skills for manufacturing equipment, thereby enhancing
overall system performance and operational efficiency.
Age: 45
Gender: Male
Education: Degree in
automation engineering
Profession:
Future application specialist
Gain
• Access to tools that streamline implementing
capabilities as skills
• Improved support for integrating skills across
machines and devices
• Ongoing education and training in the latest skill
implementation technologies and practices
Pain/Frustration
• Keeping up with the ever-evolving skill sets needed
for modern manufacturing technologies
• Working with existing hardware that may not always
support the latest software
• Integrating new applications and technologies with
legacy systems can be complex and time-consuming
Goals
• Continuously improve manufacturing processes to
increase productivity and reduce waste
• Ensure seamless integration of new applications and
technologies with existing systems
• Develop applications and processes that minimize
downtime and maximize the reliability of manu-
facturing systems
Character
• Problem-solver, detail-oriented, innovative
• Methodical, precise, adaptable work style
• Clear, concise, technically adept communication
• Analytical, strategic, focused on practical solutions


# 2025-i40-capabilities (1)

## Seite 56

56
Literature
[1] A. Köcher et al., “A reference model for common understanding of capabilities and skills in manufacturing, ”
at - Automatisierungstechnik, vol. 71, no. 2, pp. 94–104, Feb. 2023, doi: 10.1515/auto-2022-0117.
[2] Plattform Industrie 4.0, Ed., “Information Model for Capabilities, Skills & Services - Definition of terminology and proposal for a technolo-
gy-independent information model for capabilities and skills in flexible manufacturing. ” Oct. 06, 2022. Accessed: Apr. 30, 2024 [Online].
Available: www.plattform-i40.de/IP/Redaktion/DE/Downloads/Publikation/CapabilitiesSkillsServices.pdf?__blob=publicationFile&v=1
[3] M. Winter et al., “Methods to describe, assign and derive capabilities from the capability, skill and service (CSS) model, ” 2024,
Otto von Guericke University Library, Magdeburg, Germany. doi: 10.25673/116039.
[4] R. Froschauer, A. Kocher, K. Meixner, S. Schmitt, and F. Spitzer, “Capabilities and Skills in Manufacturing:
A Survey Over the Last Decade of ETFA, ” in 2022 IEEE 27th International Conference on Emerging Technologies and Factory Automation
(ETFA), Stuttgart, Germany: IEEE, Sep. 2022, pp. 1–8. doi: 10.1109/ETFA52439.2022.9921560.
[5] E. Järvenpää, N. Siltala, O. Hylli, and M. Lanz, “The development of an ontology for describing the capabilities of manufacturing
resources, ” J Intell Manuf, vol. 30, no. 2, pp. 959–978, Feb. 2019, doi: 10.1007/s10845-018-1427-6.
[6] A. Köcher et al., “Automating the Development of Machine Skills and their Semantic Description, ” in 2020 25th IEEE International
Conference on Emerging Technologies and Factory Automation (ETFA), Vienna, Austria: IEEE, Sep. 2020, pp. 1013–1018. doi: 10.1109/
ETFA46521.2020.9211933.
[7] Y. Huang, S. Dhouib, and J. Malenfant, “An AAS Modeling Tool for Capability-Based Engineering of Flexible Production Lines, ” in IECON
2021 – 47th Annual Conference of the IEEE Industrial Electronics Society, Toronto, ON, Canada: IEEE, Oct. 2021,
pp. 1–6. doi: 10.1109/IECON48115.2021.9589329.
[8] S. Grüner, M. Hoernicke, K. Stark, N. Schoch, N. Eskandani, and J. Pretlove, “Towards asset administration shell-based continuous
engineering in process industries, ” at - Automatisierungstechnik, vol. 71, no. 8, pp. 689–708, Aug. 2023, doi: 10.1515/auto-2023-0012.
[9] “DIN 8580:2022-12, Manufacturing processes - Terms and definitions, division. ”
[10] TGL 25000-1: Verfahrenstechnik – Grundoperationen – Klassifikation, Fachsbereichstandard, Leipzig., 1974.
[11] R. Studer, V. R. Benjamins, and D. Fensel, “Knowledge engineering: Principles and methods, ” Data & Knowledge Engineering,
vol. 25, no. 1–2, pp. 161–197, Mar. 1998, doi: 10.1016/S0169-023X(97)00056-6.
[12] J. Bock, T. Kleinert, T. Klausmann, A. Köcher, M. Simon, and M. Winter, “A Formal Approach to Defining Effects of Manufacturing
Functions, ” presented at the IEEE ETFA 2024 IEEE International Conference on Emerging Technologies and Factory Automation,
Padova, Italy: IEEE, accepted 2024.
[13] “VDI/VDE/NAMUR 2658 Part 1:2019-10, Automation engineering of modular systems in the process industry -
General concept and interfaces. ”
[14] “ISA-TR88.00.02-2022, Machine and Unit States: An implementation example of ISA-88.00.01. ”
[15] “Control Component Type (Version 1.0). ” [Online].
Available: https:/ /github.com/admin-shell-io/submodel-templates/tree/main/published/Control%20Component%20Type/1/0


# 2025-i40-capabilities (1)

## Seite 57

57
[16] S. Bergweiler, S. Hamm, J. Hermann, C. Plociennik, M. Ruskowski, and A. Wagner, “Production Level 4 – Der Weg zur zukunftssicheren
und verlässlichen Produktion, ” 2022. [Online].
Available: https:/ /smartfactory.de/wp-content/uploads/2022/05/SF_Whitepaper-Production-Level-4_WEB.pdf
[17] S. Jungbluth, A. Witton, J. Hermann, and M. Ruskowski, “Architecture for Shared Production Leveraging Asset Administration Shell and
Gaia-X, ” in 2023 IEEE 21st International Conference on Industrial Informatics (INDIN), IEEE, 2023, pp. 1–8.
[18] “PAS 1018:2002-12, Essential structure for the description of services in the procurement stage [withdrawn]. ”
[19] “IDTA – working together to promote the Digital Twin. ” [Online]. Available: https:/ /industrialdigitaltwin.org/
[20] “VDI/VDE 3682 Blatt 1:2015-05, Formalised process descriptions - Concept and graphic representation. ”
[21] “VDI 2860:1990-05, Assembly and handling; handling functions, handling units; terminology, definitions and symbols (withdrawn). ”
[22] “VDI/VDE 2206:2021-11, Development of mechatronic and cyber-physical systems. ”
[23] “ANSI/ISA–88.00.01–2010, Batch Control Part 1 - Models and Terminology. ”
[24] S. Grimm et al., “Capabilities and skills for manufacturing planning in an automotive use case scenario, ” at-Automatisierungstechnik,
vol. 71, no. 2, pp. 151–163, 2023.
[25] ISA-TR88.00.02-2022, Machine and Unit States: An implementation example of ISA-88.00.01.
[26] Cornell University, “Information Technology Professional Services Agreement, ” 2021. [Online].
Available: https:/ /finance.cornell.edu/sites/default/files/it-prof-services-agrmt.pdf
[27] European Union, Ed., “Directive 2014/24/EU of the European Parliament and of the Council of 26 February 2014 on public procurement
and repealing Directive 2004/18/EC Text with EEA relevance. ” Feb. 26, 2014. Accessed: May 24, 2024. [Online].
Available: https:/ /eur-lex.europa.eu/legal-content/EN/TXT/?qid=1415180510261&uri=CELEX:32014L0024
[28] International Chamber of Commerce (ICC), “ICC Model Contract | International Sale (Manufactured Goods). ” ICC Services, 2020.
Accessed: Jul. 24, 2024. [Online]. Available: https:/ /library.iccwbo.org/content/clp/BOOKS/BK_0052/clp-mc-811e.htm
AUTHORS
Jürgen Bock (Technische Hochschule Ingolstadt), Christian Diedrich (Otto von Guericke University), Stephan
Grimm (Siemens AG), Simon Jungbluth (Technologie-Initiative SmartFactory KL e. V.), Tobias Klausmann (Lenze
SE), Tobias Kleinert (RWTH Aachen University), Aljosha Köcher (Helmut Schmidt University), Kristof Meixner
(CDL-SQI, TU Wien), Thomas Müller (PSI Automotive & Industry GmbH), Jörn Peschke (Siemens AG), Miriam
Schleipen (EKS InTec GmbH), Siwara Schmitt (Fraunhofer IESE), Boris Schnebel (Fraunhofer IOSB), Marco Simon
(Technologie-Initiative SmartFactory KL e. V.), Melanie Stolze (Institut für Automation und Kommunikation e.V.),
Chris Urban (Otto von Guericke University), Luis Miguel Vieira da Silva (Helmut Schmidt University),
Michael Winter (RWTH Aachen University).
THIS PUBLICATION WAS CREATED BY THE WORKING GROUP "SEMANTICS AND INTERACTION OF I4.0 COMPONENTS" OF PLATTFORM
INDUSTRIE 4.0.
